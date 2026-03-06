"""Remittance service — settlement run logic with delta-based calculation."""

from datetime import datetime

from sqlmodel import Session, select

from app.models import (
    AdjustmentType,
    Remittance,
    RemittanceGenerateResponse,
    RemittanceLineItem,
    RemittanceLineItemPublic,
    RemittancePublic,
    RemittanceStatus,
    User,
    WorkLog,
)


class RemittanceService:
    """Handles the settlement run: generating remittances for all users."""

    @staticmethod
    def _compute_worklog_current_amount(worklog: WorkLog, hourly_rate: float) -> float:
        """Calculate the current total amount for a worklog (same logic as WorkLogService)."""
        time_hours = 0.0
        for seg in worklog.time_segments:
            if seg.is_active:
                delta = seg.end_time - seg.start_time
                time_hours += delta.total_seconds() / 3600.0

        base_amount = round(time_hours * hourly_rate, 2)

        adjustment_total = 0.0
        for adj in worklog.adjustments:
            if adj.adjustment_type == AdjustmentType.BONUS:
                adjustment_total += adj.amount
            else:
                adjustment_total -= adj.amount

        return round(base_amount + adjustment_total, 2)

    @staticmethod
    def _get_previously_settled_amount(worklog_id, session: Session) -> float:
        """Sum of all amounts previously settled for this worklog
        across all SUCCESS remittances."""
        statement = (
            select(RemittanceLineItem)
            .join(Remittance)
            .where(
                RemittanceLineItem.worklog_id == worklog_id,
                Remittance.status == RemittanceStatus.SUCCESS,
            )
        )
        line_items = session.exec(statement).all()
        return round(sum(li.amount_settled for li in line_items), 2)

    @staticmethod
    def generate_remittances(session: Session) -> RemittanceGenerateResponse:
        """Run settlement for all users.

        For each user:
        1. Iterate over all their worklogs.
        2. Compute the current total amount for each worklog.
        3. Subtract what has already been successfully settled (delta approach).
        4. If the sum of deltas ≠ 0, create a Remittance + line items.
        5. Mark the remittance as SUCCESS (simulating a successful payout).
        """
        now = datetime.utcnow()
        period_label = now.strftime("%Y-%m")

        users = session.exec(select(User)).all()
        generated: list[RemittancePublic] = []
        users_processed = 0

        for user in users:
            worklogs = session.exec(
                select(WorkLog).where(WorkLog.user_id == user.id)
            ).all()

            if not worklogs:
                continue

            line_item_data: list[dict] = []
            total_delta = 0.0

            for wl in worklogs:
                current_amount = RemittanceService._compute_worklog_current_amount(
                    wl, user.hourly_rate
                )
                previously_settled = RemittanceService._get_previously_settled_amount(
                    wl.id, session
                )
                delta = round(current_amount - previously_settled, 2)

                if delta != 0:
                    line_item_data.append(
                        {"worklog_id": wl.id, "amount_settled": delta}
                    )
                    total_delta += delta

            total_delta = round(total_delta, 2)

            if total_delta == 0 and not line_item_data:
                continue

            # Create remittance — start as PENDING
            remittance = Remittance(
                user_id=user.id,
                total_amount=total_delta,
                status=RemittanceStatus.PENDING,
                period_label=period_label,
                created_at=now,
                updated_at=now,
            )
            session.add(remittance)
            session.flush()  # Get the remittance.id

            # Create line items
            db_line_items: list[RemittanceLineItem] = []
            for lid in line_item_data:
                li = RemittanceLineItem(
                    remittance_id=remittance.id,
                    worklog_id=lid["worklog_id"],
                    amount_settled=lid["amount_settled"],
                )
                session.add(li)
                db_line_items.append(li)

            # Simulate successful payout
            remittance.status = RemittanceStatus.SUCCESS
            remittance.updated_at = datetime.utcnow()
            session.add(remittance)
            session.flush()

            users_processed += 1

            # Build response
            line_items_public = [
                RemittanceLineItemPublic(
                    id=li.id,
                    worklog_id=li.worklog_id,
                    amount_settled=li.amount_settled,
                )
                for li in db_line_items
            ]

            generated.append(
                RemittancePublic(
                    id=remittance.id,
                    user_id=remittance.user_id,
                    total_amount=remittance.total_amount,
                    status=remittance.status,
                    period_label=remittance.period_label,
                    created_at=remittance.created_at,
                    line_items=line_items_public,
                )
            )

        session.commit()

        return RemittanceGenerateResponse(
            message=f"Settlement run completed. {users_processed} user(s) processed.",
            remittances=generated,
            total_users_processed=users_processed,
        )
