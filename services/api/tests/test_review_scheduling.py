from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, ReviewTaskModel
from app.models.contracts import MaterialStatus, ReviewTaskStatus, TaskType
from app.services.shared.review_scheduling import MAX_EASE, MIN_EASE, sm2_schedule
from conftest import auth_headers

_CHILD = {
    "name": "小和", "age": 8, "level": "grade3", "learning_goal": "复习",
    "preferred_review_duration_minutes": 10, "parent_notes": "",
}


# --------------------------- pure SM-2 --------------------------- #


def test_sm2_correct_streak_grows_interval() -> None:
    first = sm2_schedule(correct=True, repetitions=0, ease_factor=2.5, interval_days=0)
    assert first.repetitions == 1 and first.interval_days == 1 and first.ease_factor > 2.5
    second = sm2_schedule(correct=True, repetitions=1, ease_factor=first.ease_factor, interval_days=1)
    assert second.repetitions == 2 and second.interval_days == 6
    third = sm2_schedule(correct=True, repetitions=2, ease_factor=second.ease_factor, interval_days=6)
    assert third.repetitions == 3 and third.interval_days == round(6 * third.ease_factor)


def test_sm2_miss_resets_and_lowers_ease() -> None:
    miss = sm2_schedule(correct=False, repetitions=5, ease_factor=2.5, interval_days=40)
    assert miss.repetitions == 0 and miss.interval_days == 1 and miss.ease_factor == 2.3


def test_sm2_ease_is_clamped() -> None:
    low = sm2_schedule(correct=False, repetitions=0, ease_factor=1.35, interval_days=1)
    assert low.ease_factor == MIN_EASE  # floored
    high = ease = 2.7
    for _ in range(5):
        high = sm2_schedule(correct=True, repetitions=3, ease_factor=high, interval_days=10).ease_factor
    assert high == MAX_EASE  # capped


# --------------------------- endpoint integration --------------------------- #


def _create_child(api_client, headers) -> str:
    resp = api_client.post("/v1/children", json=_CHILD, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _seed_listen_choice(child_id: str, task_id: str) -> None:
    db = SessionLocal()
    try:
        mat_id = f"mat_{child_id}"
        if db.get(CourseMaterialModel, mat_id) is None:
            db.add(CourseMaterialModel(
                id=mat_id, child_id=child_id, lesson_date=date(2026, 7, 31),
                title="动物", topic="动物", status=MaterialStatus.ready.value,
                uploaded_at=datetime.now(timezone.utc), learning_assets=[],
            ))
        db.add(ReviewTaskModel(
            id=task_id, child_id=child_id, material_id=mat_id,
            task_type=TaskType.listen_choice.value, difficulty="repeat",
            content_json={"choices": ["cat", "dog"], "correct_answer": "cat"},
            due_date=datetime.now(timezone.utc), status=ReviewTaskStatus.pending.value,
        ))
        db.commit()
    finally:
        db.close()


def _sr(task_id: str):
    db = SessionLocal()
    try:
        t = db.get(ReviewTaskModel, task_id)
        return t.repetitions, t.interval_days, t.due_date, t.status
    finally:
        db.close()


def test_correct_answer_schedules_task_forward_and_drops_from_due(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    _seed_listen_choice(child_id, "rt_sched_ok")

    # answer correctly → repetitions 1, interval 1, due ~tomorrow, still pending
    resp = api_client.post(
        "/v1/practice-sessions",
        json={"child_id": child_id, "review_task_ids": ["rt_sched_ok"],
              "task_results": [{"task_id": "rt_sched_ok", "answer": "cat"}]},
        headers=headers,
    )
    assert resp.status_code == 201 and resp.json()["score"] == 100.0
    reps, interval, due, status = _sr("rt_sched_ok")
    assert reps == 1 and interval == 1 and status == "pending"
    # scheduled forward (~1 day); normalize tz since sqlite returns naive datetimes
    due_naive = due.replace(tzinfo=None)
    assert due_naive > datetime.utcnow() + timedelta(hours=12)

    # it's no longer "due today"
    due_now = api_client.get(f"/v1/review-tasks?child_id={child_id}&due_only=true", headers=headers).json()
    assert all(t["id"] != "rt_sched_ok" for t in due_now["items"])
    # but still visible in the full list
    all_tasks = api_client.get(f"/v1/review-tasks?child_id={child_id}", headers=headers).json()
    assert any(t["id"] == "rt_sched_ok" and t["repetitions"] == 1 for t in all_tasks["items"])


def test_wrong_answer_keeps_task_due_soon(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    _seed_listen_choice(child_id, "rt_sched_miss")

    resp = api_client.post(
        "/v1/practice-sessions",
        json={"child_id": child_id, "review_task_ids": ["rt_sched_miss"],
              "task_results": [{"task_id": "rt_sched_miss", "answer": "dog"}]},  # wrong
        headers=headers,
    )
    assert resp.status_code == 201 and resp.json()["score"] == 0.0
    reps, interval, _due, _status = _sr("rt_sched_miss")
    assert reps == 0 and interval == 1  # reset, due again in a day
