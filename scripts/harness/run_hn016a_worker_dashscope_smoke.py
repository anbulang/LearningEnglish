from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
WORKERS_ROOT = ROOT / "services" / "workers"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-016A"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    try:
        summary = _run_worker_smoke(evidence_dir=evidence_dir, started=started)
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "dashscope",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "worker-dashscope-real-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_worker_smoke(*, evidence_dir: Path, started: float) -> dict:
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError("DASHSCOPE_API_KEY is required for HN-016A DashScope worker smoke")

    work_dir = Path(tempfile.mkdtemp(prefix="learning-english-hn016a-worker-"))
    os.environ["APP_ENV"] = "testing"
    os.environ["DATABASE_URL"] = f"sqlite:///{work_dir / 'worker-smoke.db'}"
    os.environ["LOCAL_STORAGE_PATH"] = str(work_dir / "uploads")
    os.environ["PUBLIC_BASE_URL"] = "http://testserver"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["MEDIA_PROVIDER"] = "real"
    os.environ["MEDIA_IMAGE_PROVIDER"] = "dashscope"
    os.environ["MEDIA_TTS_PROVIDER"] = "dashscope"

    from app.core.db import Base, SessionLocal, engine  # noqa: E402
    from app.core.settings import get_settings  # noqa: E402
    from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, StoredAssetModel  # noqa: E402
    from app.models.contracts import MaterialStatus  # noqa: E402
    from app.services.mappers import course_material_from_model  # noqa: E402
    from workers_app.tasks import process_learning_asset_media  # noqa: E402

    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        parent = ParentAccountModel(
            id="parent_dashscope_media",
            display_name="家长",
            wechat_union_id="wechat_union_dashscope_media",
            wechat_open_id="wechat_open_dashscope_media",
        )
        child = ChildProfileModel(
            id="child_dashscope_media",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_dashscope_real",
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
                    "text": "rabbit",
                    "kind": "word",
                    "translation": "兔子",
                    "source_page_index": 1,
                    "source_visual_description": "A rabbit can hop fast.",
                    "pronunciation_text": "rabbit",
                    "image_prompt": "Colorful child-friendly rabbit flashcard.",
                    "primary_accent": "us",
                }
            ],
        )
        db.add_all([parent, child, material])
        db.commit()

    worker_result = process_learning_asset_media("material_dashscope_real")

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_dashscope_real")
        if material is None:
            raise RuntimeError("material was not persisted")
        material_payload = course_material_from_model(material).model_dump(mode="json")
        stored_assets = db.query(StoredAssetModel).filter_by(owner_id=material.id).all()
        stored_payload = [
            {
                "owner_type": asset.owner_type,
                "object_key": asset.object_key,
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
                "url": asset.url,
            }
            for asset in stored_assets
        ]

    worker_storage_dir = evidence_dir / "worker-storage"
    if worker_storage_dir.exists():
        shutil.rmtree(worker_storage_dir)
    source_storage = work_dir / "uploads"
    if source_storage.exists():
        shutil.copytree(source_storage, worker_storage_dir)

    material_path = evidence_dir / "worker-dashscope-real-material.json"
    material_path.write_text(json.dumps(material_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stored_assets_path = evidence_dir / "worker-dashscope-real-stored-assets.json"
    stored_assets_path.write_text(json.dumps(stored_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    learning_assets = material_payload.get("learning_assets") or []
    first_asset = learning_assets[0] if learning_assets else {}
    ready_count = sum(
        1
        for key in ("generated_image_status", "tts_us_status", "tts_uk_status")
        if first_asset.get(key) == "ready"
    )
    summary = {
        "status": "passed" if worker_result.get("status") == "ready" and ready_count == 3 else "failed",
        "provider": "dashscope",
        "media_provider": "real",
        "media_image_provider": "dashscope",
        "media_tts_provider": "dashscope",
        "worker_result": worker_result,
        "material_id": material_payload.get("id"),
        "learning_asset_count": len(learning_assets),
        "ready_media_count": ready_count,
        "stored_asset_count": len(stored_payload),
        "material_json": str(material_path),
        "stored_assets_json": str(stored_assets_path),
        "worker_storage_dir": str(worker_storage_dir),
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    summary_path = evidence_dir / "worker-dashscope-real-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if summary["status"] != "passed":
        raise RuntimeError(f"worker smoke failed: {summary}")
    return summary


if __name__ == "__main__":
    main()
