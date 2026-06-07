from __future__ import annotations

from datetime import date, datetime, timezone

from app.db.models import CourseMaterialModel, MaterialParseJobModel
from app.models.contracts import (
    CourseMaterial,
    JobStatus,
    LearningAsset,
    MaterialParseJob,
    MaterialStatus,
    MediaGenerationStatus,
    PrimaryAccent,
    SourceBoundingBox,
)
from app.services.shared.mappers import course_material_from_model, material_job_from_model


def test_learning_asset_round_trips_media_fields() -> None:
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        translation="女王",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.05, y=0.14, width=0.43, height=0.35),
        source_visual_description="迷宫里的女王。",
        pronunciation_text="queen",
        image_prompt="参考讲义女王线稿，生成彩色女王插图。",
        difficulty="easy",
        teaching_note="让孩子先找女王，再读 queen。",
        is_core=True,
        generated_image_status=MediaGenerationStatus.ready,
        generated_image_url="http://testserver/mock-media/hn014/images/queen.svg",
        generated_image_object_key="mock_media/hn014/images/queen.svg",
        tts_us_status=MediaGenerationStatus.ready,
        tts_us_url="http://testserver/mock-media/hn014/tts/us/queen.m4a",
        tts_us_object_key="mock_media/hn014/tts/us/queen.m4a",
        tts_uk_status=MediaGenerationStatus.ready,
        tts_uk_url="http://testserver/mock-media/hn014/tts/uk/queen.m4a",
        tts_uk_object_key="mock_media/hn014/tts/uk/queen.m4a",
        primary_accent=PrimaryAccent.us,
    )

    payload = asset.model_dump(mode="json")
    assert payload["source_bbox"] == {"x": 0.05, "y": 0.14, "width": 0.43, "height": 0.35}
    assert payload["generated_image_status"] == "ready"
    assert payload["primary_accent"] == "us"
    assert LearningAsset(**payload).tts_uk_url.endswith("/tts/uk/queen.m4a")


def test_material_and_job_include_learning_assets() -> None:
    asset = LearningAsset(
        id="asset_duck",
        text="duck",
        kind="word",
        translation="鸭子",
        source_page_index=1,
        pronunciation_text="duck",
        image_prompt="参考讲义鸭子线稿，生成彩色鸭子插图。",
        difficulty="easy",
        teaching_note="让孩子指图读 duck。",
    )

    material = CourseMaterial(
        id="material_1",
        child_id="child_1",
        teacher_name="外教课",
        lesson_date=date(2026, 5, 12),
        title="Qq Storybook",
        status=MaterialStatus.ready,
        learning_assets=[asset],
    )
    job = MaterialParseJob(
        id="job_1",
        material_id="material_1",
        status=JobStatus.needs_review,
        started_at=datetime.now(timezone.utc),
        draft_learning_assets=[asset],
    )

    assert material.learning_assets[0].text == "duck"
    assert job.draft_learning_assets[0].translation == "鸭子"


def test_mappers_round_trip_learning_assets_from_json_columns() -> None:
    asset_payload = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        translation="女王",
        source_page_index=2,
        source_bbox=SourceBoundingBox(x=0.1, y=0.2, width=0.3, height=0.4),
        generated_image_status=MediaGenerationStatus.ready,
        generated_image_url="http://testserver/mock-media/hn014/images/queen.svg",
        tts_us_status=MediaGenerationStatus.ready,
        tts_us_url="http://testserver/mock-media/hn014/tts/us/queen.m4a",
        primary_accent=PrimaryAccent.us,
    ).model_dump(mode="json")

    material_model = CourseMaterialModel(
        id="material_1",
        child_id="child_1",
        teacher_name="外教课",
        lesson_date=date(2026, 5, 12),
        title="Qq Storybook",
        topic="alphabet",
        status=MaterialStatus.ready.value,
        source_images=[],
        source_image_keys=[],
        normalized_image_keys=[],
        pdf_url="",
        pdf_key="",
        file_size_bytes=0,
        ocr_text="",
        tags=[],
        image_records=[],
        learning_assets=[asset_payload],
    )
    job_model = MaterialParseJobModel(
        id="job_1",
        material_id="material_1",
        status=JobStatus.needs_review.value,
        confidence_summary="",
        warnings=[],
        started_at=datetime.now(timezone.utc),
        draft_title="Qq Storybook",
        draft_topic="alphabet",
        draft_vocabulary=[],
        draft_sentences=[],
        draft_image_records=[],
        draft_learning_assets=[asset_payload],
    )

    material = course_material_from_model(material_model)
    job = material_job_from_model(job_model)

    assert material.learning_assets[0].source_bbox == SourceBoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
    assert material.learning_assets[0].generated_image_status == MediaGenerationStatus.ready
    assert job.draft_learning_assets[0].text == "queen"
    assert job.draft_learning_assets[0].tts_us_url.endswith("/tts/us/queen.m4a")
