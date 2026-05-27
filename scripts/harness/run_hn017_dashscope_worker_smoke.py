from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
WORKERS_ROOT = ROOT / "services" / "workers"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))

SAMPLE_AUDIO_URL = (
    "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
)


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-017"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    try:
        summary = _run_worker_smoke(evidence_dir=evidence_dir, started=started)
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "dashscope",
            "audio_url": SAMPLE_AUDIO_URL,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "dashscope-worker-smoke-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_worker_smoke(*, evidence_dir: Path, started: float) -> dict:
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError("DASHSCOPE_API_KEY is required for HN-017 DashScope worker smoke")

    work_dir = Path(tempfile.mkdtemp(prefix="learning-english-hn017-worker-"))
    os.environ["APP_ENV"] = "testing"
    os.environ["DATABASE_URL"] = f"sqlite:///{work_dir / 'worker-smoke.db'}"
    os.environ["LOCAL_STORAGE_PATH"] = str(work_dir / "uploads")
    os.environ["PUBLIC_BASE_URL"] = "http://testserver"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["SPEECH_PROVIDER"] = "dashscope"
    os.environ["SPEECH_ASSESSMENT_PROVIDER"] = "dashscope"
    os.environ.pop("SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL", None)

    from app.core.db import Base, SessionLocal, engine  # noqa: E402
    from app.core.settings import get_settings  # noqa: E402
    from app.db.models import (  # noqa: E402
        ChildProfileModel,
        CourseMaterialModel,
        ParentAccountModel,
        SpeakingAttemptModel,
        StoredAssetModel,
        WeeklyReportModel,
    )
    from app.models.contracts import MaterialStatus, SpeakingAttemptStatus  # noqa: E402
    from app.services.mappers import speaking_attempt_from_model  # noqa: E402
    from workers_app.tasks import score_speaking_attempt  # noqa: E402

    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    object_key = "speaking_attempt/attempt_dashscope_worker/input.wav"
    audio_path = work_dir / "uploads" / object_key
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30, trust_env=os.environ.get("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true") as client:
        response = client.get(SAMPLE_AUDIO_URL)
        response.raise_for_status()
        audio_path.write_bytes(response.content)

    with SessionLocal() as db:
        parent = ParentAccountModel(
            id="parent_dashscope_worker",
            display_name="家长",
            wechat_union_id="wechat_union_dashscope_worker",
            wechat_open_id="wechat_open_dashscope_worker",
        )
        child = ChildProfileModel(
            id="child_dashscope_worker",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_dashscope_worker",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 25),
            title="DashScope Worker Smoke",
            topic="Speaking",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_hello",
                    "text": "Hello world.",
                    "kind": "sentence",
                    "translation": "你好，世界。",
                    "pronunciation_text": "Hello world.",
                    "primary_accent": "us",
                }
            ],
        )
        attempt = SpeakingAttemptModel(
            id="attempt_dashscope_worker",
            child_id=child.id,
            material_id=material.id,
            learning_asset_id="asset_hello",
            prompt_text="跟读：Hello world.",
            target_text="Hello world.",
            audio_url=SAMPLE_AUDIO_URL,
            audio_object_key=object_key,
            audio_content_type="audio/wav",
            audio_size_bytes=audio_path.stat().st_size,
            status=SpeakingAttemptStatus.recording_uploaded.value,
        )
        audio_asset = StoredAssetModel(
            id="stored_dashscope_worker_audio",
            owner_type="speaking_attempt",
            owner_id=attempt.id,
            bucket="learning-english",
            object_key=object_key,
            content_type="audio/wav",
            size_bytes=audio_path.stat().st_size,
            url=SAMPLE_AUDIO_URL,
        )
        db.add_all([parent, child, material, attempt, audio_asset])
        db.commit()

    worker_result = score_speaking_attempt("attempt_dashscope_worker")

    with SessionLocal() as db:
        attempt = db.get(SpeakingAttemptModel, "attempt_dashscope_worker")
        report = db.query(WeeklyReportModel).filter_by(child_id="child_dashscope_worker").first()
        if attempt is None:
            raise RuntimeError("attempt was not persisted")
        attempt_payload = speaking_attempt_from_model(attempt).model_dump(mode="json")
        report_payload = None
        if report is not None:
            report_payload = {
                "id": report.id,
                "speaking_attempts": report.speaking_attempts,
                "weak_items": report.weak_items or [],
                "recommended_actions": report.recommended_actions or [],
            }

    attempt_path = evidence_dir / "dashscope-worker-smoke-attempt.json"
    attempt_path.write_text(json.dumps(attempt_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "passed" if worker_result.get("status") == "scored" else "failed",
        "provider": attempt_payload.get("provider"),
        "audio_url": SAMPLE_AUDIO_URL,
        "worker_result": worker_result,
        "attempt_status": attempt_payload.get("status"),
        "transcript": attempt_payload.get("transcript"),
        "overall_score": attempt_payload.get("overall_score"),
        "pronunciation_score": attempt_payload.get("pronunciation_score"),
        "report": report_payload,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "attempt_json": str(attempt_path),
    }
    summary_path = evidence_dir / "dashscope-worker-smoke-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if summary["status"] != "passed":
        raise RuntimeError(f"worker smoke failed: {summary}")
    return summary


if __name__ == "__main__":
    main()
