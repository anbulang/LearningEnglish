import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select


_TEST_ROOT = tempfile.mkdtemp(prefix="learning-english-worker-speaking-test-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT}/worker.db"
os.environ["LOCAL_STORAGE_PATH"] = f"{_TEST_ROOT}/uploads"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["JWT_SECRET"] = "learning-english-worker-test-secret-at-least-32-bytes"
os.environ["AI_PROVIDER"] = "stub"
os.environ["SPEECH_PROVIDER"] = "stub"

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))
WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.append(str(WORKERS_ROOT))

from app.core.db import Base, SessionLocal, engine
from app.core.settings import get_settings
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    ParentAccountModel,
    SpeakingAttemptModel,
    StoredAssetModel,
    WeeklyReportModel,
)
from app.models.contracts import MaterialStatus, SpeakingAttemptStatus
from workers_app.celery_app import celery_app
from workers_app.tasks import score_speaking_attempt


def test_speaking_attempt_task_is_registered() -> None:
    assert "speaking.score_attempt" in celery_app.tasks


def test_score_speaking_attempt_updates_attempt_and_report() -> None:
    _configure_storage_env()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_speaking_attempt()

    result = score_speaking_attempt("attempt_test")

    assert result == {"attempt_id": "attempt_test", "status": "scored"}
    with SessionLocal() as db:
        attempt = db.get(SpeakingAttemptModel, "attempt_test")
        assert attempt is not None
        assert attempt.status == SpeakingAttemptStatus.scored.value
        assert attempt.transcript == "A rabbit can hop fast."
        assert attempt.overall_score == 88
        assert attempt.word_feedback
        report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == "child_test"))
        assert report is not None
        assert report.speaking_attempts == 1
        assert "a" in report.weak_items or "hop" in report.weak_items


def _seed_speaking_attempt() -> None:
    _configure_storage_env()
    uploads_root = os.environ["LOCAL_STORAGE_PATH"]
    object_key = "speaking_attempt/attempt_test/input.m4a"
    os.makedirs(f"{uploads_root}/speaking_attempt/attempt_test", exist_ok=True)
    with open(f"{uploads_root}/{object_key}", "wb") as handle:
        handle.write(b"fake-audio")

    with SessionLocal() as db:
        parent = ParentAccountModel(
            id="parent_test",
            display_name="家长",
            wechat_union_id="wechat_union_speaking_test",
            wechat_open_id="wechat_open_speaking_test",
        )
        child = ChildProfileModel(
            id="child_test",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_test",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 25),
            title="Run, Hop, Go!",
            topic="Phonics Rr",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_rabbit",
                    "text": "A rabbit can hop fast.",
                    "kind": "sentence",
                    "translation": "兔子能跳得很快。",
                    "pronunciation_text": "A rabbit can hop fast.",
                    "primary_accent": "us",
                }
            ],
        )
        attempt = SpeakingAttemptModel(
            id="attempt_test",
            child_id=child.id,
            material_id=material.id,
            learning_asset_id="asset_rabbit",
            prompt_text="跟读：A rabbit can hop fast.",
            target_text="A rabbit can hop fast.",
            audio_url=f"http://testserver/uploads/{object_key}",
            audio_object_key=object_key,
            audio_content_type="audio/mp4",
            audio_size_bytes=10,
            status=SpeakingAttemptStatus.recording_uploaded.value,
        )
        audio_asset = StoredAssetModel(
            id="stored_speaking_audio_test",
            owner_type="speaking_attempt",
            owner_id=attempt.id,
            bucket="learning-english",
            object_key=object_key,
            content_type="audio/mp4",
            size_bytes=10,
            url=f"http://testserver/uploads/{object_key}",
        )
        db.add_all([parent, child, material, attempt, audio_asset])
        db.commit()


def _configure_storage_env() -> None:
    os.environ["LOCAL_STORAGE_PATH"] = f"{_TEST_ROOT}/uploads"
    os.environ["SPEECH_PROVIDER"] = "stub"
    get_settings.cache_clear()
