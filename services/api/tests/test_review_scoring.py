from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, ReviewTaskModel
from app.models.contracts import MaterialStatus, ReviewTaskStatus, TaskType
from app.services.shared.review_scoring import score_review_session, score_review_task
from conftest import auth_headers

_CHILD = {
    "name": "小和", "age": 8, "level": "grade3", "learning_goal": "复习",
    "preferred_review_duration_minutes": 10, "parent_notes": "",
}


# --------------------------- pure scoring --------------------------- #


def test_score_review_task_by_type() -> None:
    # listen_choice: right pick vs wrong pick
    ok, item = score_review_task(
        task_type="listen_choice",
        content={"choices": ["cat", "dog"], "correct_answer": "cat"}, answer="cat",
    )
    assert ok and item == "cat"
    ok, item = score_review_task(
        task_type="listen_choice",
        content={"choices": ["cat", "dog"], "correct_answer": "cat"}, answer="dog",
    )
    assert not ok and item == "cat"

    # match_choice: index-paired left/right
    content = {"left": ["What is this?"], "right": ["It is a cat."], "prompt": "配对"}
    assert score_review_task(task_type="match_choice", content=content, answers=["It is a cat."])[0]
    assert not score_review_task(task_type="match_choice", content=content, answers=["wrong"])[0]

    # flashcard: honest self-rate
    assert score_review_task(task_type="flashcard", content={"word": "dog"}, answer="known")[0]
    wrong = score_review_task(task_type="flashcard", content={"word": "dog"}, answer="unknown")
    assert not wrong[0] and wrong[1] == "dog"

    # unknown/coaching types are "seen", not scored against a key
    assert score_review_task(task_type="parent_coaching", content={}, answer="")[0]


def test_score_review_session_aggregate() -> None:
    score, weak = score_review_session([(True, "cat"), (False, "dog"), (False, "bird"), (True, "fish")])
    assert score == 50.0
    assert weak == ["dog", "bird"]
    assert score_review_session([]) == (0.0, [])
    # weak points dedupe, preserve order
    assert score_review_session([(False, "dog"), (False, "dog")])[1] == ["dog"]


# --------------------------- endpoint (authoritative) --------------------------- #


def _create_child(api_client, headers) -> str:
    resp = api_client.post("/v1/children", json=_CHILD, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _seed_tasks(child_id: str) -> tuple[str, str]:
    """Seed one listen_choice (answer 'cat') + one flashcard ('dog') task for the
    child. IDs are child-derived so tests sharing the module DB don't collide.
    Returns (listen_choice_id, flashcard_id)."""
    mat_id, lc_id, fc_id = f"mat_{child_id}", f"rtlc_{child_id}", f"rtfc_{child_id}"
    db = SessionLocal()
    try:
        db.add(CourseMaterialModel(
            id=mat_id, child_id=child_id, lesson_date=date(2026, 7, 30),
            title="动物", topic="动物", status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc), learning_assets=[],
        ))
        db.add(ReviewTaskModel(
            id=lc_id, child_id=child_id, material_id=mat_id,
            task_type=TaskType.listen_choice.value, difficulty="repeat",
            content_json={"prompt": "听音选图", "choices": ["cat", "dog", "bird"], "correct_answer": "cat"},
            due_date=datetime.now(timezone.utc), status=ReviewTaskStatus.pending.value,
        ))
        db.add(ReviewTaskModel(
            id=fc_id, child_id=child_id, material_id=mat_id,
            task_type=TaskType.flashcard.value, difficulty="recognition",
            content_json={"prompt": "看词卡", "word": "dog"},
            due_date=datetime.now(timezone.utc), status=ReviewTaskStatus.pending.value,
        ))
        db.commit()
    finally:
        db.close()
    return lc_id, fc_id


def test_practice_session_scores_from_real_answers(api_client) -> None:
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    lc_id, fc_id = _seed_tasks(child_id)

    # child gets listen_choice right ("cat"), flashcard wrong (self-rate "unknown")
    resp = api_client.post(
        "/v1/practice-sessions",
        json={
            "child_id": child_id,
            "review_task_ids": [lc_id, fc_id],
            "task_results": [
                {"task_id": lc_id, "answer": "cat"},
                {"task_id": fc_id, "answer": "unknown"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    s = resp.json()
    assert s["score"] == 50.0            # 1 of 2 correct — server-computed, not 92
    assert s["weak_points"] == ["dog"]   # only the missed flashcard word

    # weekly report reflects the real weak item
    rep = api_client.get("/v1/reports/weekly", params={"child_id": child_id}, headers=headers).json()
    assert "dog" in rep["report"]["weak_items"]


def test_practice_session_legacy_score_still_supported(api_client) -> None:
    # callers that don't submit per-task answers keep the old behavior
    headers, _ = auth_headers(api_client)
    child_id = _create_child(api_client, headers)
    lc_id, fc_id = _seed_tasks(child_id)
    resp = api_client.post(
        "/v1/practice-sessions",
        json={"child_id": child_id, "review_task_ids": [lc_id, fc_id], "score": 88, "weak_points": ["dog"]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["score"] == 88
