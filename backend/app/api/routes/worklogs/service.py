"""WorkLog service — business logic for worklog queries and amount calculation."""

from datetime import datetime

from sqlmodel import Session, select

from app.models import (
    Adjustment,
    AdjustmentPublic,
    AdjustmentType,
    Remittance,
    RemittanceLineItem,
    RemittanceStatus,
    TimeSegment,
    TimeSegmentPublic,
    WorkLog,
    WorkLogListResponse,
    WorkLogPublic,
)


class WorkLogService:
    """Handles worklog listing with amount calculation and remittance filtering."""

    @staticmethod
    def _compute_amount(worklog: WorkLog, hourly_rate: float) -> float:
        """Calculate the total amount for a worklog.

        amount = (sum of active time-segment hours × hourly_rate) + adjustments
        """
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
    def _get_remittance_status(worklog: WorkLog, session: Session) -> str:
        """Determine if a worklog has been fully or partially remitted.

        REMITTED  = at least one RemittanceLineItem linked to a SUCCESS remittance.
        UNREMITTED = no successful settlement exists for this worklog.
        """
        statement = (
            select(RemittanceLineItem)
            .join(Remittance)
            .where(
                RemittanceLineItem.worklog_id == worklog.id,
                Remittance.status == RemittanceStatus.SUCCESS,
            )
        )
        result = session.exec(statement).first()
        return "REMITTED" if result else "UNREMITTED"

    @staticmethod
    def list_worklogs(
        session: Session,
        remittance_status: str | None = None,
    ) -> WorkLogListResponse:
        """List all worklogs with computed amounts, optionally filtered by
        remittance status (REMITTED / UNREMITTED)."""

        statement = select(WorkLog)
        worklogs = session.exec(statement).all()

        result: list[WorkLogPublic] = []
        for wl in worklogs:
            # Eager-loaded via relationship
            hourly_rate = wl.user.hourly_rate if wl.user else 25.0
            amount = WorkLogService._compute_amount(wl, hourly_rate)
            status = WorkLogService._get_remittance_status(wl, session)

            if remittance_status and status != remittance_status.upper():
                continue

            time_segments_public = [
                TimeSegmentPublic(
                    id=seg.id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    is_active=seg.is_active,
                    created_at=seg.created_at,
                )
                for seg in wl.time_segments
            ]

            adjustments_public = [
                AdjustmentPublic(
                    id=adj.id,
                    amount=adj.amount,
                    reason=adj.reason,
                    adjustment_type=adj.adjustment_type,
                    created_at=adj.created_at,
                )
                for adj in wl.adjustments
            ]

            result.append(
                WorkLogPublic(
                    id=wl.id,
                    user_id=wl.user_id,
                    title=wl.title,
                    description=wl.description,
                    created_at=wl.created_at,
                    amount=amount,
                    remittance_status=status,
                    time_segments=time_segments_public,
                    adjustments=adjustments_public,
                )
            )

        return WorkLogListResponse(data=result, count=len(result))
