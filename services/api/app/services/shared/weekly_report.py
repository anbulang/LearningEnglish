"""Find-or-create the current ISO-week report for a child.

Weekly reports are keyed by (child_id, week_start) where week_start is the Monday
of the ISO week — one row per child per week, giving parents multi-week history.
Shared by the API (review/child creation) and workers (speaking), so all three
write sites accumulate into the same weekly bucket.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import WeeklyReportModel

# The product serves families in China and the Celery worker runs on
# Asia/Shanghai (see services/workers/workers_app/celery_app.py). ISO-week bounds
# must be derived in that zone, or a Monday 00:00–07:59 local session lands in the
# previous week while the UI still labels it "本周". CST is a fixed UTC+8 with no
# DST since 1991, so a fixed offset is exact and avoids a tzdata dependency.
PRODUCT_TZ = timezone(timedelta(hours=8))


def local_date(moment: datetime | None = None) -> date:
    """Return the calendar date of ``moment`` in the product timezone.

    ``moment`` defaults to now. Naive datetimes (e.g. sqlite reads) are assumed UTC.
    """
    if moment is None:
        moment = datetime.now(PRODUCT_TZ)
    elif moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(PRODUCT_TZ).date()


def current_week_bounds(today: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) for the ISO week containing ``today`` (product tz)."""
    today = today or local_date()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def get_or_create_current_week_report(
    db: Session,
    child_id: str,
    *,
    recommended_actions: list[str] | None = None,
    when: date | None = None,
) -> WeeklyReportModel:
    """Return the child's report for an ISO week, creating it if absent.

    ``when`` selects the week (defaults to the current UTC week). Async writers
    should pass the event's *occurrence* date — e.g. ``attempt.created_at.date()``
    for speaking scoring — so an attempt made on Sunday but processed after the
    Monday boundary still counts toward the week it happened in.

    Concurrency-safe against the ``uq_weekly_reports_child_week`` constraint: two
    racing writers (e.g. a review POST and the speaking worker) can both try to
    create the week's row; the loser recovers via SAVEPOINT + re-select rather
    than 500-ing on the unique violation.
    """
    week_start, week_end = current_week_bounds(when)

    def _find() -> WeeklyReportModel | None:
        return db.scalar(
            select(WeeklyReportModel).where(
                WeeklyReportModel.child_id == child_id,
                WeeklyReportModel.week_start == week_start,
            )
        )

    report = _find()
    if report is not None:
        return report

    try:
        # Add + flush INSIDE the savepoint so a unique violation rolls back to the
        # SAVEPOINT (not the outer transaction) and the loser can recover.
        with db.begin_nested():
            report = WeeklyReportModel(
                child_id=child_id,
                week_start=week_start,
                week_end=week_end,
                recommended_actions=recommended_actions or [],
            )
            db.add(report)
            db.flush()
    except IntegrityError:
        existing = _find()
        if existing is None:  # pragma: no cover - shouldn't happen after a unique violation
            raise
        return existing
    return report
