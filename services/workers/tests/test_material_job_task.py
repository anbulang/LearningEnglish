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
os.environ["AI_PROVIDER"] = "stub"

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))
WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.append(str(WORKERS_ROOT))

from app.core.db import Base, SessionLocal, engine
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ReviewTaskModel,
    StoredAssetModel,
)
from app.models.contracts import JobStatus, MaterialStatus, MediaGenerationStatus
from workers_app.celery_app import celery_app
from workers_app.tasks import process_learning_asset_media, process_material_job


def test_material_job_task_is_registered() -> None:
    assert "materials.process_material_job" in celery_app.tasks
    assert "materials.process_learning_asset_media" in celery_app.tasks


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
            draft_image_records=[
                {
                    "id": "image_test",
                    "page_index": 1,
                    "source_type": "camera",
                    "original_filename": "worksheet.txt",
                    "url": "http://testserver/uploads/material/material_test/worksheet.txt",
                    "object_key": object_key,
                    "content_type": "text/plain",
                    "size_bytes": 32,
                    "image_title": "",
                    "ocr_text": "",
                    "vocabulary": [],
                    "sentences": [],
                    "details": ["图片已上传，等待 AI 识别。"],
                }
            ],
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
        assert job.draft_image_records
        assert job.draft_image_records[0]["image_title"]
        assert job.draft_learning_assets
        assert job.draft_learning_assets[0]["text"]
        assert material.image_records == job.draft_image_records
        assert material.ocr_text
    finally:
        db.close()


def test_process_material_job_marks_failed_when_provider_errors(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    uploads_root = os.environ["LOCAL_STORAGE_PATH"]
    os.makedirs(f"{uploads_root}/material/material_fail", exist_ok=True)
    object_key = "material/material_fail/worksheet.jpg"
    with open(f"{uploads_root}/{object_key}", "wb") as handle:
        handle.write(b"fake image bytes")

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_fail",
            display_name="家长",
            wechat_union_id="wechat_union_fail",
            wechat_open_id="wechat_open_fail",
        )
        child = ChildProfileModel(
            id="child_fail",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_fail",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 3, 25),
            title="Animals Around Me",
            topic="动物",
            status=MaterialStatus.processing.value,
            source_images=["http://testserver/uploads/material/material_fail/worksheet.jpg"],
            source_image_keys=[object_key],
            normalized_image_keys=[object_key],
            uploaded_at=datetime.now(timezone.utc),
            tags=["动物"],
        )
        asset = StoredAssetModel(
            id="asset_fail",
            owner_type="material",
            owner_id=material.id,
            bucket="learning-english",
            object_key=object_key,
            content_type="image/jpeg",
            size_bytes=16,
            url="http://testserver/uploads/material/material_fail/worksheet.jpg",
        )
        job = MaterialParseJobModel(
            id="job_fail",
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

    class FailingPipeline:
        def prepare_job(self, *args, **kwargs):
            raise RuntimeError("doubao provider returned 500")

    monkeypatch.setattr("workers_app.tasks.build_pipeline_service", lambda: FailingPipeline())

    result = process_material_job("job_fail")
    assert result["status"] == "failed"

    db = SessionLocal()
    try:
        job = db.get(MaterialParseJobModel, "job_fail")
        material = db.get(CourseMaterialModel, "material_fail")
        assert job is not None
        assert material is not None
        assert job.status == JobStatus.failed.value
        assert material.status == MaterialStatus.failed.value
        assert "doubao provider returned 500" in job.confidence_summary
        assert "处理失败" in job.warnings[0]
    finally:
        db.close()


def test_process_learning_asset_media_fills_mock_urls() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_media",
            display_name="家长",
            wechat_union_id="wechat_union_media",
            wechat_open_id="wechat_open_media",
        )
        child = ChildProfileModel(
            id="child_media",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_media",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 3, 25),
            title="Qq Queen",
            topic="Phonics Qq",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_queen",
                    "text": "queen",
                    "kind": "word",
                    "translation": "女王",
                    "primary_accent": "us",
                }
            ],
        )
        knowledge_pack = KnowledgePackModel(
            id="knowledge_media",
            material_id=material.id,
            topic="Phonics Qq",
            difficulty_band="repeat",
            lesson_summary="复习 queen。",
            review_recommendation="先看图听音。",
            vocabulary_items=[
                {
                    "id": "word_queen",
                    "knowledge_pack_id": "knowledge_media",
                    "word": "queen",
                    "meaning_cn": "女王",
                    "image_url": "",
                    "audio_url": "",
                    "example_sentence": "",
                }
            ],
            sentence_patterns=[],
        )
        review_task = ReviewTaskModel(
            id="task_queen",
            child_id=child.id,
            material_id=material.id,
            task_type="flashcard",
            difficulty="easy",
            content_json={
                "asset_id": "asset_queen",
                "prompt": "看图跟读：queen",
                "word": "queen",
                "translation": "女王",
                "image_url": "",
                "audio_url": "",
            },
            due_date=datetime.now(timezone.utc),
            status="pending",
        )
        db.add_all([parent, child, material, knowledge_pack, review_task])
        db.commit()
    finally:
        db.close()

    result = process_learning_asset_media("material_media")
    assert result["status"] == "ready"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"] == "http://testserver/mock-media/hn014/images/queen.svg"
        assert asset["tts_us_status"] == "ready"
        assert asset["tts_us_url"] == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
        assert asset["tts_uk_status"] == "ready"
        assert asset["tts_uk_url"] == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"
        knowledge_pack = db.get(KnowledgePackModel, "knowledge_media")
        assert knowledge_pack is not None
        assert knowledge_pack.vocabulary_items[0]["image_url"] == "http://testserver/mock-media/hn014/images/queen.svg"
        assert knowledge_pack.vocabulary_items[0]["audio_url"] == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
        review_task = db.get(ReviewTaskModel, "task_queen")
        assert review_task is not None
        assert review_task.content_json["image_url"] == "http://testserver/mock-media/hn014/images/queen.svg"
        assert review_task.content_json["audio_url"] == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
    finally:
        db.close()


def test_process_learning_asset_media_preserves_user_primary_accent(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_media_accent",
            display_name="家长",
            wechat_union_id="wechat_union_media_accent",
            wechat_open_id="wechat_open_media_accent",
        )
        child = ChildProfileModel(
            id="child_media_accent",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_media_accent",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 3, 25),
            title="Qq Queen",
            topic="Phonics Qq",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_queen",
                    "text": "queen",
                    "kind": "word",
                    "translation": "女王",
                    "primary_accent": "us",
                }
            ],
        )
        db.add_all([parent, child, material])
        db.commit()
    finally:
        db.close()

    class ConcurrentAccentProvider:
        def __init__(self, public_base_url: str) -> None:
            self.public_base_url = public_base_url.rstrip("/")

        def apply(self, assets):
            with SessionLocal() as db:
                material = db.get(CourseMaterialModel, "material_media_accent")
                assert material is not None
                current = dict(material.learning_assets[0])
                current["primary_accent"] = "uk"
                material.learning_assets = [current]
                db.add(material)
                db.commit()
            return [
                assets[0].model_copy(
                        update={
                            "generated_image_status": MediaGenerationStatus.ready,
                            "generated_image_url": f"{self.public_base_url}/mock-media/hn014/images/queen.svg",
                            "tts_us_status": MediaGenerationStatus.ready,
                            "tts_us_url": f"{self.public_base_url}/mock-media/hn014/tts/us/queen.m4a",
                            "tts_uk_status": MediaGenerationStatus.ready,
                            "tts_uk_url": f"{self.public_base_url}/mock-media/hn014/tts/uk/queen.m4a",
                        }
                    )
            ]

    monkeypatch.setattr("workers_app.tasks.HN014MockMediaProvider", ConcurrentAccentProvider)

    result = process_learning_asset_media("material_media_accent")
    assert result["status"] == "ready"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_accent")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["primary_accent"] == "uk"
        assert asset["tts_uk_url"] == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"
    finally:
        db.close()


def test_process_learning_asset_media_returns_missing_for_unknown_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    result = process_learning_asset_media("material_missing")

    assert result == {"material_id": "material_missing", "status": "missing"}
