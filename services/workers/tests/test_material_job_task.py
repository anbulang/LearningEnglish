import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select


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
from app.models.contracts import JobStatus, LearningAsset, MaterialStatus, MediaGenerationStatus
from app.services.learning_asset_media import GeneratedMedia, MediaProviderConfigurationError
from workers_app.celery_app import celery_app
from workers_app.tasks import process_learning_asset_media, process_material_job


def _seed_media_material(material_id: str, asset_id: str, text: str) -> None:
    uploads_root = os.environ["LOCAL_STORAGE_PATH"]
    object_key = f"material/{material_id}/source.png"
    os.makedirs(f"{uploads_root}/material/{material_id}", exist_ok=True)
    with open(f"{uploads_root}/{object_key}", "wb") as handle:
        handle.write(b"not a real image")

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id=f"parent_{material_id}",
            display_name="家长",
            wechat_union_id=f"wechat_union_{material_id}",
            wechat_open_id=f"wechat_open_{material_id}",
        )
        child = ChildProfileModel(
            id=f"child_{material_id}",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id=material_id,
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 3, 25),
            title=f"{text.title()} Practice",
            topic="Phonics",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            source_images=[f"http://testserver/uploads/{object_key}"],
            source_image_keys=[object_key],
            normalized_image_keys=[object_key],
            learning_assets=[
                {
                    "id": asset_id,
                    "text": text,
                    "kind": "word",
                    "translation": "练习词",
                    "primary_accent": "us",
                    "pronunciation_text": text,
                    "image_prompt": f"A child-friendly flashcard image for {text}.",
                }
            ],
        )
        source_asset = StoredAssetModel(
            id=f"source_{material_id}",
            owner_type="material",
            owner_id=material.id,
            bucket="learning-english",
            object_key=object_key,
            content_type="image/png",
            size_bytes=16,
            url=f"http://testserver/uploads/{object_key}",
        )
        knowledge_pack = KnowledgePackModel(
            id=f"knowledge_{material_id}",
            material_id=material.id,
            topic="Phonics",
            difficulty_band="repeat",
            lesson_summary=f"复习 {text}。",
            review_recommendation="先看图听音。",
            vocabulary_items=[
                {
                    "id": f"word_{asset_id}",
                    "knowledge_pack_id": f"knowledge_{material_id}",
                    "word": text,
                    "meaning_cn": "练习词",
                    "image_url": "",
                    "audio_url": "",
                    "example_sentence": "",
                }
            ],
            sentence_patterns=[],
        )
        review_task = ReviewTaskModel(
            id=f"task_{asset_id}",
            child_id=child.id,
            material_id=material.id,
            task_type="flashcard",
            difficulty="easy",
            content_json={
                "asset_id": asset_id,
                "prompt": f"看图跟读：{text}",
                "word": text,
                "translation": "练习词",
                "image_url": "",
                "audio_url": "",
            },
            due_date=datetime.now(timezone.utc),
            status="pending",
        )
        db.add_all([parent, child, material, source_asset, knowledge_pack, review_task])
        db.commit()
    finally:
        db.close()


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


def test_process_learning_asset_media_generates_and_stores_provider_media(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media", "asset_queen", "queen")

    class FakeImageProvider:
        def generate(self, asset, prompt, reference_image_path):
            assert asset.id == "asset_queen"
            assert "queen" in prompt
            assert reference_image_path is None
            return GeneratedMedia(b"image-bytes", "image/png", ".png")

    class FakeTTSProvider:
        def synthesize(self, text, accent):
            assert text == "queen"
            return GeneratedMedia(f"{accent}-audio".encode(), "audio/mpeg", ".mp3")

    class FakeBundle:
        def __init__(self) -> None:
            self.image_provider = FakeImageProvider()
            self.tts_provider = FakeTTSProvider()
            self.closed = False

        def close(self) -> None:
            self.closed = True

    bundle = FakeBundle()
    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: bundle)

    result = process_learning_asset_media("material_media")
    assert result["status"] == "ready"
    assert bundle.closed is True
    second_result = process_learning_asset_media("material_media")
    assert second_result["status"] == "ready"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media")
        assert material is not None
        asset = material.learning_assets[0]
        image_url = "http://testserver/uploads/generated/media/material_media/asset_queen/image.png"
        tts_us_url = "http://testserver/uploads/generated/media/material_media/asset_queen/tts-us.mp3"
        tts_uk_url = "http://testserver/uploads/generated/media/material_media/asset_queen/tts-uk.mp3"
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"] == image_url
        assert asset["tts_us_status"] == "ready"
        assert asset["tts_us_url"] == tts_us_url
        assert asset["tts_uk_status"] == "ready"
        assert asset["tts_uk_url"] == tts_uk_url
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert len(stored_assets) == 3
        assert {row.object_key for row in stored_assets} == {
            "generated/media/material_media/asset_queen/image.png",
            "generated/media/material_media/asset_queen/tts-us.mp3",
            "generated/media/material_media/asset_queen/tts-uk.mp3",
        }
        knowledge_pack = db.get(KnowledgePackModel, "knowledge_material_media")
        assert knowledge_pack is not None
        assert knowledge_pack.vocabulary_items[0]["image_url"] == image_url
        assert knowledge_pack.vocabulary_items[0]["audio_url"] == tts_us_url
        review_task = db.get(ReviewTaskModel, "task_asset_queen")
        assert review_task is not None
        assert review_task.content_json["image_url"] == image_url
        assert review_task.content_json["audio_url"] == tts_us_url
    finally:
        db.close()


def test_process_learning_asset_media_preserves_hn014_mock_manifest_urls() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_mock", "asset_queen", "queen")

    result = process_learning_asset_media("material_media_mock")
    assert result["status"] == "ready"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_mock")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"] == "http://testserver/mock-media/hn014/images/queen.svg"
        assert asset["generated_image_object_key"] == "mock_media/hn014/images/queen.svg"
        assert asset["source_bbox"] == {"x": 0.05, "y": 0.14, "width": 0.43, "height": 0.35}
        assert asset["tts_us_url"] == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
        assert asset["tts_uk_url"] == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert stored_assets == []
    finally:
        db.close()


def test_process_learning_asset_media_fails_unknown_hn014_mock_asset() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_mock_unknown", "asset_unknown", "not-in-manifest")

    result = process_learning_asset_media("material_media_mock_unknown")
    assert result["status"] == "failed"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_mock_unknown")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "failed"
        assert asset["tts_us_status"] == "failed"
        assert asset["tts_uk_status"] == "failed"
        assert "HN-014 mock media asset not found" in asset["generated_image_error"]
    finally:
        db.close()


def test_process_learning_asset_media_keeps_tts_when_image_generation_fails(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_partial", "asset_queen", "queen")

    class FailingImageProvider:
        def generate(self, asset, prompt, reference_image_path):
            raise RuntimeError("image provider timeout")

    class FakeTTSProvider:
        def synthesize(self, text, accent):
            return GeneratedMedia(f"{accent}-audio".encode(), "audio/mpeg", ".mp3")

    class FakeBundle:
        image_provider = FailingImageProvider()
        tts_provider = FakeTTSProvider()

        def close(self) -> None:
            pass

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: FakeBundle())

    result = process_learning_asset_media("material_media_partial")
    assert result["status"] == "partial"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_partial")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "failed"
        assert "图片生成失败" in asset["generated_image_error"]
        assert asset["tts_us_status"] == "ready"
        assert asset["tts_uk_status"] == "ready"
    finally:
        db.close()


def test_process_learning_asset_media_marks_all_media_failed_when_bundle_configuration_fails(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_config_fail", "asset_queen", "queen")

    def raise_configuration_error():
        raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", raise_configuration_error)

    result = process_learning_asset_media("material_media_config_fail")

    assert result == {"material_id": "material_media_config_fail", "status": "failed"}
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_config_fail")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "failed"
        assert asset["tts_us_status"] == "failed"
        assert asset["tts_uk_status"] == "failed"
        assert "媒体生成配置失败" in asset["generated_image_error"]
        assert "OPENAI_API_KEY is required when MEDIA_PROVIDER=real" in asset["generated_image_error"]
        assert "媒体生成配置失败" in asset["tts_us_error"]
        assert "媒体生成配置失败" in asset["tts_uk_error"]
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert stored_assets == []
    finally:
        db.close()


def test_process_learning_asset_media_preserves_ready_media_when_bundle_configuration_fails(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_config_fail_ready", "asset_queen", "queen")
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_config_fail_ready")
        assert material is not None
        ready_asset = dict(material.learning_assets[0])
        ready_asset.update(
            {
                "generated_image_status": "ready",
                "generated_image_url": "http://testserver/uploads/generated/media/material_media_config_fail_ready/asset_queen/image.png",
                "generated_image_object_key": "generated/media/material_media_config_fail_ready/asset_queen/image.png",
                "generated_image_error": "",
                "tts_us_status": "ready",
                "tts_us_url": "http://testserver/uploads/generated/media/material_media_config_fail_ready/asset_queen/tts-us.mp3",
                "tts_us_object_key": "generated/media/material_media_config_fail_ready/asset_queen/tts-us.mp3",
                "tts_us_error": "",
                "tts_uk_status": "ready",
                "tts_uk_url": "http://testserver/uploads/generated/media/material_media_config_fail_ready/asset_queen/tts-uk.mp3",
                "tts_uk_object_key": "generated/media/material_media_config_fail_ready/asset_queen/tts-uk.mp3",
                "tts_uk_error": "",
            }
        )
        material.learning_assets = [ready_asset]
        db.add(material)
        db.commit()
    finally:
        db.close()

    def raise_configuration_error():
        raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", raise_configuration_error)

    result = process_learning_asset_media("material_media_config_fail_ready")

    assert result == {"material_id": "material_media_config_fail_ready", "status": "failed"}
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_config_fail_ready")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"] == ready_asset["generated_image_url"]
        assert asset["generated_image_object_key"] == ready_asset["generated_image_object_key"]
        assert asset["generated_image_error"] == ""
        assert asset["tts_us_status"] == "ready"
        assert asset["tts_us_url"] == ready_asset["tts_us_url"]
        assert asset["tts_us_object_key"] == ready_asset["tts_us_object_key"]
        assert asset["tts_us_error"] == ""
        assert asset["tts_uk_status"] == "ready"
        assert asset["tts_uk_url"] == ready_asset["tts_uk_url"]
        assert asset["tts_uk_object_key"] == ready_asset["tts_uk_object_key"]
        assert asset["tts_uk_error"] == ""
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert stored_assets == []
    finally:
        db.close()


def test_process_learning_asset_media_stops_saving_when_archived_during_generation(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_media_archive_mid_generation", "asset_queen", "queen")

    class ArchivingImageProvider:
        def generate(self, asset, prompt, reference_image_path):
            with SessionLocal() as db:
                material = db.get(CourseMaterialModel, "material_media_archive_mid_generation")
                assert material is not None
                material.status = MaterialStatus.archived.value
                db.add(material)
                db.commit()
            return GeneratedMedia(b"image-bytes", "image/png", ".png")

    class FakeTTSProvider:
        def synthesize(self, text, accent):
            return GeneratedMedia(f"{accent}-audio".encode(), "audio/mpeg", ".mp3")

    class FakeBundle:
        image_provider = ArchivingImageProvider()
        tts_provider = FakeTTSProvider()

        def close(self) -> None:
            pass

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: FakeBundle())

    result = process_learning_asset_media("material_media_archive_mid_generation")
    assert result == {"material_id": "material_media_archive_mid_generation", "status": "archived"}

    db = SessionLocal()
    try:
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert stored_assets == []
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

    class ConcurrentImageProvider:
        def generate(self, asset, prompt, reference_image_path):
            return GeneratedMedia(b"image-bytes", "image/png", ".png")

    class ConcurrentTTSProvider:
        def synthesize(self, text, accent):
            with SessionLocal() as db:
                material = db.get(CourseMaterialModel, "material_media_accent")
                assert material is not None
                current = dict(material.learning_assets[0])
                current["primary_accent"] = "uk"
                material.learning_assets = [current]
                db.add(material)
                db.commit()
            return GeneratedMedia(f"{accent}-audio".encode(), "audio/mpeg", ".mp3")

    class ConcurrentBundle:
        image_provider = ConcurrentImageProvider()
        tts_provider = ConcurrentTTSProvider()

        def close(self) -> None:
            pass

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: ConcurrentBundle())

    result = process_learning_asset_media("material_media_accent")
    assert result["status"] == "ready"

    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_media_accent")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["primary_accent"] == "uk"
        assert asset["tts_uk_url"] == "http://testserver/uploads/generated/media/material_media_accent/asset_queen/tts-uk.mp3"
    finally:
        db.close()


def test_process_learning_asset_media_returns_missing_for_unknown_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    result = process_learning_asset_media("material_missing")

    assert result == {"material_id": "material_missing", "status": "missing"}


def test_process_material_job_skips_archived_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_archived_job",
            display_name="家长",
            wechat_union_id="wechat_union_archived_job",
            wechat_open_id="wechat_open_archived_job",
        )
        child = ChildProfileModel(
            id="child_archived_job",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_archived_job",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 15),
            title="Archived Worksheet",
            topic="Phonics",
            status=MaterialStatus.archived.value,
            uploaded_at=datetime.now(timezone.utc),
            tags=[],
        )
        job = MaterialParseJobModel(
            id="job_archived",
            material_id=material.id,
            status=JobStatus.processing.value,
            confidence_summary="等待 OCR 与解析。",
            draft_title=material.title,
            draft_topic=material.topic,
            draft_vocabulary=[],
            draft_sentences=[],
        )
        db.add_all([parent, child, material, job])
        db.commit()
    finally:
        db.close()

    result = process_material_job("job_archived")

    assert result == {"job_id": "job_archived", "status": "archived"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_archived_job")
        job = db.get(MaterialParseJobModel, "job_archived")
        assert material is not None
        assert job is not None
        assert material.status == MaterialStatus.archived.value
        assert job.status == JobStatus.processing.value
        assert job.draft_vocabulary == []


def test_process_learning_asset_media_skips_archived_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_archived_media",
            display_name="家长",
            wechat_union_id="wechat_union_archived_media",
            wechat_open_id="wechat_open_archived_media",
        )
        child = ChildProfileModel(
            id="child_archived_media",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_archived_media",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 15),
            title="Qq Queen",
            topic="Phonics Qq",
            status=MaterialStatus.archived.value,
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

    result = process_learning_asset_media("material_archived_media")

    assert result == {"material_id": "material_archived_media", "status": "archived"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_archived_media")
        assert material is not None
        assert material.status == MaterialStatus.archived.value
        assert material.learning_assets[0].get("generated_image_status") is None


def test_process_learning_asset_media_skips_if_archived_before_processing_write(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_archived_media_race",
            display_name="家长",
            wechat_union_id="wechat_union_archived_media_race",
            wechat_open_id="wechat_open_archived_media_race",
        )
        child = ChildProfileModel(
            id="child_archived_media_race",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_archived_media_race",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 15),
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

    class ArchiveBeforeProcessingAsset:
        def __init__(self, **item) -> None:
            self._asset = LearningAsset(**item)

        def model_copy(self, update=None):
            if (update or {}).get("generated_image_status") == MediaGenerationStatus.processing:
                with SessionLocal() as db:
                    material = db.get(CourseMaterialModel, "material_archived_media_race")
                    assert material is not None
                    material.status = MaterialStatus.archived.value
                    db.add(material)
                    db.commit()
            return self._asset.model_copy(update=update)

    monkeypatch.setattr("workers_app.tasks.LearningAsset", ArchiveBeforeProcessingAsset)

    result = process_learning_asset_media("material_archived_media_race")

    assert result == {"material_id": "material_archived_media_race", "status": "archived"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_archived_media_race")
        assert material is not None
        assert material.status == MaterialStatus.archived.value
        asset = material.learning_assets[0]
        assert "generated_image_status" not in asset
        assert "tts_us_status" not in asset
        assert "tts_uk_status" not in asset
