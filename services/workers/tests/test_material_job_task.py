import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path


_TEST_ROOT = tempfile.mkdtemp(prefix="learning-english-worker-test-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT}/worker.db"
os.environ["LOCAL_STORAGE_PATH"] = f"{_TEST_ROOT}/uploads"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["JWT_SECRET"] = "learning-english-worker-test-secret-at-least-32-bytes"

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))
WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.append(str(WORKERS_ROOT))

from app.core.db import Base, SessionLocal, engine
from app.db.models import ChildProfileModel, CourseMaterialModel, MaterialParseJobModel, ParentAccountModel, StoredAssetModel
from app.models.contracts import JobStatus, MaterialStatus
from workers_app.tasks import process_material_job


def test_process_material_job_updates_db_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    uploads_root = os.environ["LOCAL_STORAGE_PATH"]
    os.makedirs(f"{uploads_root}/material/material_test", exist_ok=True)
    object_key = "material/material_test/worksheet.txt"
    with open(f"{uploads_root}/{object_key}", "wb") as handle:
        handle.write(b"cat dog bird\nWhat is this?\nIt is a cat.")

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_test",
            display_name="家长",
            wechat_union_id="wechat_union_test",
            wechat_open_id="wechat_open_test",
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
            lesson_date=date(2026, 3, 25),
            title="Animals Around Me",
            topic="动物",
            status=MaterialStatus.processing.value,
            source_images=["http://testserver/uploads/material/material_test/worksheet.txt"],
            source_image_keys=[object_key],
            normalized_image_keys=[object_key],
            uploaded_at=datetime.now(timezone.utc),
            tags=["动物"],
        )
        asset = StoredAssetModel(
            id="asset_test",
            owner_type="material",
            owner_id=material.id,
            bucket="learning-english",
            object_key=object_key,
            content_type="text/plain",
            size_bytes=32,
            url="http://testserver/uploads/material/material_test/worksheet.txt",
        )
        job = MaterialParseJobModel(
            id="job_test",
            material_id=material.id,
            status=JobStatus.processing.value,
            confidence_summary="等待 OCR 与解析。",
            draft_title=material.title,
            draft_topic=material.topic,
            draft_vocabulary=[],
            draft_sentences=[],
        )
        db.add_all([parent, child, material, asset, job])
        db.commit()
    finally:
        db.close()

    result = process_material_job("job_test")
    assert result["status"] == "needs_review"

    db = SessionLocal()
    try:
        job = db.get(MaterialParseJobModel, "job_test")
        material = db.get(CourseMaterialModel, "material_test")
        assert job is not None
        assert material is not None
        assert job.status == JobStatus.needs_review.value
        assert material.status == MaterialStatus.needs_review.value
        assert job.draft_vocabulary
        assert material.ocr_text
    finally:
        db.close()
