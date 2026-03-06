"""Seed the database with initial data: superuser + sample worklog data."""

import logging
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.db import engine
from app.models import (
    Adjustment,
    AdjustmentType,
    TimeSegment,
    User,
    WorkLog,
)
from app import crud
from app.core.config import settings
from app.models import UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _seed_worklogs(session: Session) -> None:
    """Create sample workers, worklogs, time segments, and adjustments."""
    # Check if seed data already exists
    existing = session.exec(select(WorkLog)).first()
    if existing:
        logger.info("Seed worklog data already exists — skipping.")
        return

    # ── Worker 1 ──────────────────────────────────────────────────────
    worker1 = session.exec(
        select(User).where(User.email == "worker1@example.com")
    ).first()
    if not worker1:
        worker1_create = UserCreate(
            email="worker1@example.com",
            password="worker1pass",
            full_name="Alice Johnson",
            hourly_rate=30.0,
            is_superuser=False,
        )
        worker1 = crud.create_user(session=session, user_create=worker1_create)
        logger.info("Created worker1: Alice Johnson")

    # ── Worker 2 ──────────────────────────────────────────────────────
    worker2 = session.exec(
        select(User).where(User.email == "worker2@example.com")
    ).first()
    if not worker2:
        worker2_create = UserCreate(
            email="worker2@example.com",
            password="worker2pass",
            full_name="Bob Smith",
            hourly_rate=45.0,
            is_superuser=False,
        )
        worker2 = crud.create_user(session=session, user_create=worker2_create)
        logger.info("Created worker2: Bob Smith")

    # ── Worker 3 ──────────────────────────────────────────────────────
    worker3 = session.exec(
        select(User).where(User.email == "worker3@example.com")
    ).first()
    if not worker3:
        worker3_create = UserCreate(
            email="worker3@example.com",
            password="worker3pass",
            full_name="Carol Davis",
            hourly_rate=50.0,
            is_superuser=False,
        )
        worker3 = crud.create_user(session=session, user_create=worker3_create)
        logger.info("Created worker3: Carol Davis")

    now = datetime.utcnow()

    # ── Worklogs for Worker 1 (Alice) ─────────────────────────────────
    wl1 = WorkLog(
        user_id=worker1.id,
        title="API Integration Module",
        description="Building REST API integration with third-party service",
        created_at=now - timedelta(days=10),
    )
    session.add(wl1)

    wl2 = WorkLog(
        user_id=worker1.id,
        title="Unit Test Suite",
        description="Writing comprehensive unit tests for payment module",
        created_at=now - timedelta(days=5),
    )
    session.add(wl2)

    # ── Worklogs for Worker 2 (Bob) ───────────────────────────────────
    wl3 = WorkLog(
        user_id=worker2.id,
        title="Database Schema Redesign",
        description="Migrating from legacy schema to normalized design",
        created_at=now - timedelta(days=8),
    )
    session.add(wl3)

    wl4 = WorkLog(
        user_id=worker2.id,
        title="Performance Optimization",
        description="Optimizing slow queries and adding caching layer",
        created_at=now - timedelta(days=3),
    )
    session.add(wl4)

    # ── Worklogs for Worker 3 (Carol) ─────────────────────────────────
    wl5 = WorkLog(
        user_id=worker3.id,
        title="Security Audit Report",
        description="Conducting security audit and documenting findings",
        created_at=now - timedelta(days=7),
    )
    session.add(wl5)

    session.flush()

    # ── Time Segments ─────────────────────────────────────────────────
    # WL1: 2 active segments (3h + 2h = 5h), 1 inactive (disputed)
    segments = [
        TimeSegment(
            worklog_id=wl1.id,
            start_time=now - timedelta(days=10, hours=8),
            end_time=now - timedelta(days=10, hours=5),
            is_active=True,
        ),
        TimeSegment(
            worklog_id=wl1.id,
            start_time=now - timedelta(days=9, hours=6),
            end_time=now - timedelta(days=9, hours=4),
            is_active=True,
        ),
        TimeSegment(
            worklog_id=wl1.id,
            start_time=now - timedelta(days=8, hours=4),
            end_time=now - timedelta(days=8, hours=2),
            is_active=False,  # Disputed / removed
        ),
        # WL2: 1 active segment (4h)
        TimeSegment(
            worklog_id=wl2.id,
            start_time=now - timedelta(days=5, hours=10),
            end_time=now - timedelta(days=5, hours=6),
            is_active=True,
        ),
        # WL3: 2 active segments (5h + 3h = 8h)
        TimeSegment(
            worklog_id=wl3.id,
            start_time=now - timedelta(days=8, hours=9),
            end_time=now - timedelta(days=8, hours=4),
            is_active=True,
        ),
        TimeSegment(
            worklog_id=wl3.id,
            start_time=now - timedelta(days=7, hours=7),
            end_time=now - timedelta(days=7, hours=4),
            is_active=True,
        ),
        # WL4: 1 active segment (2h)
        TimeSegment(
            worklog_id=wl4.id,
            start_time=now - timedelta(days=3, hours=6),
            end_time=now - timedelta(days=3, hours=4),
            is_active=True,
        ),
        # WL5: 2 active segments (4h + 3h = 7h)
        TimeSegment(
            worklog_id=wl5.id,
            start_time=now - timedelta(days=7, hours=8),
            end_time=now - timedelta(days=7, hours=4),
            is_active=True,
        ),
        TimeSegment(
            worklog_id=wl5.id,
            start_time=now - timedelta(days=6, hours=7),
            end_time=now - timedelta(days=6, hours=4),
            is_active=True,
        ),
    ]
    for seg in segments:
        session.add(seg)

    # ── Adjustments ───────────────────────────────────────────────────
    adjustments = [
        # WL1: -$20 quality deduction
        Adjustment(
            worklog_id=wl1.id,
            amount=20.0,
            reason="Minor quality issue in API error handling",
            adjustment_type=AdjustmentType.DEDUCTION,
        ),
        # WL3: +$50 bonus for early delivery
        Adjustment(
            worklog_id=wl3.id,
            amount=50.0,
            reason="Early delivery bonus",
            adjustment_type=AdjustmentType.BONUS,
        ),
        # WL5: -$30 deduction for incomplete section
        Adjustment(
            worklog_id=wl5.id,
            amount=30.0,
            reason="Incomplete compliance section",
            adjustment_type=AdjustmentType.DEDUCTION,
        ),
    ]
    for adj in adjustments:
        session.add(adj)

    session.commit()
    logger.info("Seeded worklog data: 3 workers, 5 worklogs, 9 time segments, 3 adjustments")


def init() -> None:
    with Session(engine) as session:
        # Create superuser if not exists
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()
        if not user:
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            )
            crud.create_user(session=session, user_create=user_in)
            logger.info("Superuser created.")

        # Seed worklog sample data
        _seed_worklogs(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
