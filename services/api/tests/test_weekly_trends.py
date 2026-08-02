from __future__ import annotations

from datetime import timedelta

from app.core.db import SessionLocal
from app.db.models import WeeklyReportModel
from app.services.shared.weekly_report import current_week_bounds
from conftest import auth_headers

_CHILD = {
    "name": "小趋", "age": 8, "level": "grade3", "learning_goal": "复习",
    "preferred_review_duration_minutes": 10, "parent_notes": "",
}


def _create_child(api_client, headers) -> str:
    resp = api_client.post("/v1/children", json=_CHILD, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _seed_past_week(child_id: str, *, weeks_ago: int, completed: int) -> None:
    """Insert a report for an earlier ISO week (bypassing the API clock)."""
    monday, _ = current_week_bounds()
    start = monday - timedelta(days=7 * weeks_ago)
    db = SessionLocal()
    try:
        db.add(WeeklyReportModel(
            child_id=child_id,
            week_start=start,
            week_end=start + timedelta(days=6),
            completed_sessions=completed,
            reviewed_words=completed * 2,
            speaking_attempts=completed,
            weak_items=["dog"],
        ))
        db.commit()
    finally:
        db.close()


def test_child_creation_seeds_current_week_report(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    monday, sunday = current_week_bounds()
    db = SessionLocal()
    try:
        reports = db.query(WeeklyReportModel).filter(WeeklyReportModel.child_id == child_id).all()
        assert len(reports) == 1
        assert reports[0].week_start == monday and reports[0].week_end == sunday
    finally:
        db.close()


def test_multiple_weeks_coexist_and_trends_orders_oldest_first(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)  # current-week report
    _seed_past_week(child_id, weeks_ago=2, completed=1)
    _seed_past_week(child_id, weeks_ago=1, completed=3)

    resp = api_client.get(f"/v1/reports/trends?child_id={child_id}", headers=headers)
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 3
    # oldest -> newest for left-to-right charting
    starts = [p["week_start"] for p in points]
    assert starts == sorted(starts)
    assert points[0]["completed_sessions"] == 1
    assert points[1]["completed_sessions"] == 3
    assert points[1]["weak_item_count"] == 1


def test_trends_zero_fills_inactive_weeks_and_trims_leading_gaps(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)  # current-week row (completed 0)
    _seed_past_week(child_id, weeks_ago=3, completed=2)  # gap at -2 and -1

    resp = api_client.get(f"/v1/reports/trends?child_id={child_id}&weeks=8", headers=headers)
    assert resp.status_code == 200
    points = resp.json()["points"]
    # consecutive calendar weeks from earliest activity (-3) to current (0) = 4 points
    assert len(points) == 4
    assert points[0]["completed_sessions"] == 2  # -3
    assert points[1]["completed_sessions"] == 0  # -2 zero-filled
    assert points[2]["completed_sessions"] == 0  # -1 zero-filled
    # week starts are consecutive Mondays
    starts = [p["week_start"] for p in points]
    assert starts == sorted(starts) and len(set(starts)) == 4


def test_practice_accumulates_into_current_week_not_past(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    _seed_past_week(child_id, weeks_ago=1, completed=5)

    # a review this week must land in the CURRENT-week bucket, leaving the past week intact
    resp = api_client.post(
        "/v1/practice-sessions",
        json={"child_id": child_id, "review_task_ids": [], "task_results": []},
        headers=headers,
    )
    assert resp.status_code == 201

    monday, _ = current_week_bounds()
    db = SessionLocal()
    try:
        current = db.query(WeeklyReportModel).filter(
            WeeklyReportModel.child_id == child_id,
            WeeklyReportModel.week_start == monday,
        ).one()
        assert current.completed_sessions == 1
        past = db.query(WeeklyReportModel).filter(
            WeeklyReportModel.child_id == child_id,
            WeeklyReportModel.week_start == monday - timedelta(days=7),
        ).one()
        assert past.completed_sessions == 5  # untouched
    finally:
        db.close()


def test_trends_weeks_param_clamped_and_child_scoped(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    for w in range(1, 4):
        _seed_past_week(child_id, weeks_ago=w, completed=w)

    # weeks=2 → only the 2 most recent weeks returned
    resp = api_client.get(f"/v1/reports/trends?child_id={child_id}&weeks=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["points"]) == 2

    # a child the parent doesn't own (or that doesn't exist) → 404
    resp = api_client.get("/v1/reports/trends?child_id=child_does_not_exist", headers=headers)
    assert resp.status_code == 404


def test_weekly_returns_empty_current_week_snapshot_when_no_activity(api_client) -> None:
    """No current-week row → honest zero snapshot for THIS week, never an older week's counters."""
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    # drop the auto-created current-week report, leave only a past week with real counters
    monday, _ = current_week_bounds()
    db = SessionLocal()
    try:
        db.query(WeeklyReportModel).filter(
            WeeklyReportModel.child_id == child_id,
            WeeklyReportModel.week_start == monday,
        ).delete()
        db.commit()
    finally:
        db.close()
    _seed_past_week(child_id, weeks_ago=1, completed=4)

    resp = api_client.get(f"/v1/reports/weekly?child_id={child_id}", headers=headers)
    assert resp.status_code == 200
    report = resp.json()["report"]
    assert report["completed_sessions"] == 0  # NOT last week's 4
    assert report["week_start"] == monday.isoformat()
    # last week's counters are still visible in the trend history
    trends = api_client.get(f"/v1/reports/trends?child_id={child_id}", headers=headers).json()
    assert any(p["completed_sessions"] == 4 for p in trends["points"])
