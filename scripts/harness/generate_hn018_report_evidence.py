from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

test_root = tempfile.mkdtemp(prefix="learning-english-hn018-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{test_root}/hn018.db"
os.environ["LOCAL_STORAGE_PATH"] = f"{test_root}/uploads"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["JWT_SECRET"] = "learning-english-hn018-secret-at-least-32-bytes"
os.environ["AI_PROVIDER"] = "stub"
os.environ["MEDIA_PROVIDER"] = "mock"
os.environ["SPEECH_PROVIDER"] = "stub"
os.environ["SPEECH_ASSESSMENT_PROVIDER"] = "stub"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    CourseMaterialModel,
    PracticeSessionModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
)
from app.main import app  # noqa: E402
from app.models.contracts import MaterialStatus, ReviewTaskStatus, SpeakingAttemptStatus, TaskType  # noqa: E402


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-018"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with TestClient(app) as client:
        headers = _auth_headers(client)
        child_id = _create_child(client, headers)
        _seed_report_data(child_id)
        response = client.get("/v1/reports/weekly", params={"child_id": child_id}, headers=headers)
        response.raise_for_status()
        report = response.json()["report"]

    (evidence_dir / "weekly-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "child_id": child_id,
        "report_summary": report["report_summary"],
        "asset_mastery_count": len(report["asset_mastery"]),
        "material_summary_count": len(report["material_summaries"]),
        "mastery_statuses": {
            item["asset_id"]: item["mastery_status"] for item in report["asset_mastery"]
        },
        "evidence": {
            "weekly_report_json": str(evidence_dir / "weekly-report.json"),
        },
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _auth_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/v1/auth/wechat/login", json={"auth_code": "hn018-report-parent"})
    login.raise_for_status()
    login_payload = login.json()
    if login_payload["status"] == "authenticated":
        token = login_payload["tokens"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    bind_token = login_payload["bind_token"]
    otp = client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138000"},
    )
    otp.raise_for_status()
    bind = client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138000",
            "otp_code": otp.json()["debug_code"],
        },
    )
    bind.raise_for_status()
    token = bind.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_child(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "更喜欢看图认词",
        },
        headers=headers,
    )
    response.raise_for_status()
    return response.json()["id"]


def _seed_report_data(child_id: str) -> None:
    with SessionLocal() as db:
        material = CourseMaterialModel(
            id="material_hn018_report",
            child_id=child_id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 25),
            title="Run, Hop, Go!",
            topic="Phonics Rr",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_rabbit",
                    "text": "rabbit",
                    "kind": "word",
                    "translation": "兔子",
                    "generated_image_url": "https://cdn.test/rabbit.png",
                    "tts_us_url": "https://cdn.test/rabbit-us.mp3",
                    "primary_accent": "us",
                },
                {
                    "id": "asset_sentence",
                    "text": "A rabbit can hop fast.",
                    "kind": "sentence",
                    "translation": "兔子能跳得很快。",
                    "generated_image_url": "https://cdn.test/rabbit-hop.png",
                    "primary_accent": "us",
                },
            ],
        )
        completed_task = ReviewTaskModel(
            id="task_hn018_rabbit",
            child_id=child_id,
            material_id=material.id,
            task_type=TaskType.flashcard.value,
            difficulty="easy",
            content_json={"asset_id": "asset_rabbit", "text": "rabbit", "prompt": "看图跟读：rabbit"},
            due_date=datetime.now(timezone.utc),
            status=ReviewTaskStatus.completed.value,
        )
        pending_task = ReviewTaskModel(
            id="task_hn018_sentence",
            child_id=child_id,
            material_id=material.id,
            task_type=TaskType.speaking_prompt.value,
            difficulty="repeat",
            content_json={
                "asset_id": "asset_sentence",
                "text": "A rabbit can hop fast.",
                "prompt": "跟读句子：A rabbit can hop fast.",
            },
            due_date=datetime.now(timezone.utc),
            status=ReviewTaskStatus.pending.value,
        )
        session = PracticeSessionModel(
            child_id=child_id,
            review_task_ids=[completed_task.id],
            score=86,
            weak_points=["A rabbit can hop fast."],
        )
        attempt = SpeakingAttemptModel(
            id="attempt_hn018_rabbit",
            child_id=child_id,
            material_id=material.id,
            learning_asset_id="asset_rabbit",
            prompt_text="Read rabbit aloud.",
            target_text="rabbit",
            audio_url="https://cdn.test/attempt.m4a",
            audio_object_key="speaking/attempt.m4a",
            transcript="rabbit",
            pronunciation_score=0.91,
            overall_score=92,
            accuracy_score=93,
            fluency_score=90,
            completeness_score=95,
            feedback="rabbit 读得清楚。",
            status=SpeakingAttemptStatus.scored.value,
        )
        db.add_all([material, completed_task, pending_task, session, attempt])
        db.commit()


if __name__ == "__main__":
    main()
