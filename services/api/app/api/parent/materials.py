from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_storage
from app.core.db import get_db
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
    StoredAssetModel,
)
from app.models.contracts import (
    CourseMaterial,
    JobStatus,
    LearningAsset,
    LearningAssetPrimaryAccentUpdate,
    MaterialCreateResponse,
    MaterialDetailResponse,
    MaterialStatus,
    MediaGenerationStatus,
    PrimaryAccent,
)
from app.services.shared.mappers import course_material_from_model, material_job_from_model
from app.services.shared.job_queue import enqueue_material_job

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[CourseMaterial])
def list_materials(
    child_id: Optional[str] = None,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[CourseMaterial]:
    child_ids = db.scalars(
        select(ChildProfileModel.id).where(ChildProfileModel.parent_account_id == current_parent.id)
    ).all()
    stmt = select(CourseMaterialModel).where(
        CourseMaterialModel.child_id.in_(child_ids or [""]),
        CourseMaterialModel.status != MaterialStatus.archived.value,
    )
    if child_id:
        stmt = stmt.where(CourseMaterialModel.child_id == child_id)
    items = db.scalars(stmt.order_by(CourseMaterialModel.lesson_date.desc())).all()
    latest_job_ids = _latest_job_ids(db, [item.id for item in items])
    return [course_material_from_model(item, parse_job_id=latest_job_ids.get(item.id, "")) for item in items]


@router.get("/{material_id}", response_model=MaterialDetailResponse)
def get_material(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MaterialDetailResponse:
    material = _get_owned_material(db, current_parent.id, material_id)
    latest_job_ids = _latest_job_ids(db, [material.id])
    return MaterialDetailResponse(
        material=course_material_from_model(material, parse_job_id=latest_job_ids.get(material.id, ""))
    )


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> Response:
    material = _get_owned_material(db, current_parent.id, material_id, include_archived=True)
    if material.status == MaterialStatus.archived.value:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    material.status = MaterialStatus.archived.value
    db.add(material)
    db.execute(delete(KnowledgePackModel).where(KnowledgePackModel.material_id == material.id))
    db.execute(delete(ParentCoachingScriptModel).where(ParentCoachingScriptModel.material_id == material.id))
    db.execute(delete(ReviewTaskModel).where(ReviewTaskModel.material_id == material.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{material_id}/learning-assets/{asset_id}/primary-accent", response_model=MaterialDetailResponse)
def update_learning_asset_primary_accent(
    material_id: str,
    asset_id: str,
    payload: LearningAssetPrimaryAccentUpdate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MaterialDetailResponse:
    material = _get_owned_material(db, current_parent.id, material_id)
    updated_assets: list[LearningAsset] = []
    found = False
    for raw_asset in material.learning_assets or []:
        asset = LearningAsset(**raw_asset)
        if asset.id == asset_id:
            if payload.primary_accent == PrimaryAccent.uk and not _audio_available(asset, PrimaryAccent.uk):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="英式发音暂不可用")
            if payload.primary_accent == PrimaryAccent.us and not _audio_available(asset, PrimaryAccent.us):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="美式发音暂不可用")
            asset = asset.model_copy(update={"primary_accent": payload.primary_accent})
            found = True
        updated_assets.append(asset)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning asset not found")

    material.learning_assets = [asset.model_dump(mode="json") for asset in updated_assets]
    _backfill_primary_accent_media(db, material.id, updated_assets)
    db.add(material)
    db.commit()
    db.refresh(material)
    latest_job_ids = _latest_job_ids(db, [material.id])
    return MaterialDetailResponse(
        material=course_material_from_model(material, parse_job_id=latest_job_ids.get(material.id, ""))
    )


@router.post("", response_model=MaterialCreateResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    child_id: str = Form(...),
    teacher_name: str = Form("外教课"),
    lesson_date: date = Form(...),
    title: str = Form("待识别讲义"),
    topic: str = Form(""),
    tags: str = Form(""),
    file_sources: Optional[list[str]] = Form(None),
    files: list[UploadFile] = File(...),
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
) -> MaterialCreateResponse:
    safe_teacher_name = teacher_name.strip() or "外教课"
    safe_title = title.strip() or "待识别讲义"
    safe_topic = topic.strip()
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == child_id,
            ChildProfileModel.parent_account_id == current_parent.id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one source image is required")

    material = CourseMaterialModel(
        child_id=child_id,
        teacher_name=safe_teacher_name,
        lesson_date=lesson_date,
        title=safe_title,
        topic=safe_topic,
        status=MaterialStatus.processing.value,
        source_images=[],
        source_image_keys=[],
        normalized_image_keys=[],
        tags=[item.strip() for item in tags.split(",") if item.strip()],
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(material)
    db.flush()

    asset_rows: list[StoredAssetModel] = []
    image_records: list[dict] = []
    total_size = 0
    sources = file_sources or []
    for index, upload in enumerate(files):
        asset = storage.save_upload("material", material.id, upload)
        db.add(asset)
        db.flush()
        asset_rows.append(asset)
        total_size += asset.size_bytes
        source_type = sources[index] if index < len(sources) else "gallery"
        if source_type not in {"camera", "gallery"}:
            source_type = "gallery"
        image_records.append(
            {
                "id": f"image_{uuid4().hex[:12]}",
                "page_index": index + 1,
                "source_type": source_type,
                "original_filename": upload.filename or f"page-{index + 1}",
                "url": asset.url,
                "object_key": asset.object_key,
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
                "image_title": "",
                "ocr_text": "",
                "vocabulary": [],
                "sentences": [],
                "details": ["图片已上传，等待 AI 识别。"],
            }
        )

    material.source_images = [asset.url for asset in asset_rows]
    material.source_image_keys = [asset.object_key for asset in asset_rows]
    material.normalized_image_keys = [asset.object_key for asset in asset_rows]
    material.file_size_bytes = total_size
    material.image_records = image_records

    job = MaterialParseJobModel(
        material_id=material.id,
        status=JobStatus.processing.value,
        confidence_summary="上传完成，等待 OCR 与解析。",
        started_at=datetime.now(timezone.utc),
        warnings=[],
        draft_title=safe_title,
        draft_topic=safe_topic,
        draft_vocabulary=[],
        draft_sentences=[],
        draft_image_records=image_records,
    )
    db.add(job)
    db.commit()
    db.refresh(material)
    db.refresh(job)
    try:
        enqueue_material_job(job.id)
    except Exception as exc:
        job.status = JobStatus.failed.value
        job.finished_at = datetime.now(timezone.utc)
        job.confidence_summary = f"识别任务排队失败：{exc}"
        job.warnings = [f"识别任务排队失败：{exc}", "请稍后在 AI 校对页重新识别。"]
        material.status = MaterialStatus.failed.value
        db.add_all([job, material])
        db.commit()
        db.refresh(material)
        db.refresh(job)
    return MaterialCreateResponse(material=course_material_from_model(material), job=material_job_from_model(job))


def _get_owned_material(
    db: Session,
    parent_account_id: str,
    material_id: str,
    include_archived: bool = False,
) -> CourseMaterialModel:
    stmt = (
        select(CourseMaterialModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            CourseMaterialModel.id == material_id,
            ChildProfileModel.parent_account_id == parent_account_id,
        )
    )
    if not include_archived:
        stmt = stmt.where(CourseMaterialModel.status != MaterialStatus.archived.value)
    material = db.scalar(stmt)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def _backfill_primary_accent_media(db: Session, material_id: str, assets: list[LearningAsset]) -> None:
    asset_by_id = {asset.id: asset for asset in assets}
    asset_by_text = {asset.text.strip().lower(): asset for asset in assets if asset.text.strip()}

    knowledge_pack = db.scalar(select(KnowledgePackModel).where(KnowledgePackModel.material_id == material_id))
    if knowledge_pack is not None:
        vocabulary_items = []
        for item in knowledge_pack.vocabulary_items or []:
            asset = asset_by_text.get(str(item.get("word", "")).strip().lower())
            vocabulary_items.append(_with_primary_audio(item, asset))
        sentence_patterns = []
        for item in knowledge_pack.sentence_patterns or []:
            asset = asset_by_text.get(str(item.get("sentence", "")).strip().lower())
            sentence_patterns.append(_with_primary_audio(item, asset))
        knowledge_pack.vocabulary_items = vocabulary_items
        knowledge_pack.sentence_patterns = sentence_patterns
        db.add(knowledge_pack)

    review_tasks = db.scalars(select(ReviewTaskModel).where(ReviewTaskModel.material_id == material_id)).all()
    for task in review_tasks:
        content = dict(task.content_json or {})
        asset = asset_by_id.get(str(content.get("asset_id", "")))
        if asset is None:
            asset = asset_by_text.get(str(content.get("text") or content.get("word") or "").strip().lower())
        task.content_json = _with_primary_audio(content, asset)
        db.add(task)


def _with_primary_audio(item: dict, asset: Optional[LearningAsset]) -> dict:
    if asset is None:
        return dict(item)
    if asset.primary_accent.value == "uk":
        audio_url = asset.tts_uk_url or asset.tts_us_url
    else:
        audio_url = asset.tts_us_url or asset.tts_uk_url
    if not audio_url:
        return dict(item)
    updated = dict(item)
    updated["audio_url"] = audio_url
    return updated


def _audio_available(asset: LearningAsset, accent: PrimaryAccent) -> bool:
    if accent == PrimaryAccent.uk:
        return bool(asset.tts_uk_url) and asset.tts_uk_status != MediaGenerationStatus.failed
    return bool(asset.tts_us_url) and asset.tts_us_status != MediaGenerationStatus.failed


def media_failed_learning_assets(assets: list[LearningAsset]) -> list[dict]:
    return [
        asset.model_copy(
            update={
                "generated_image_status": MediaGenerationStatus.failed,
                "tts_us_status": MediaGenerationStatus.failed,
                "tts_uk_status": MediaGenerationStatus.failed,
            }
        ).model_dump(mode="json")
        for asset in assets
    ]


def _latest_job_ids(db: Session, material_ids: list[str]) -> dict[str, str]:
    if not material_ids:
        return {}
    rows = db.execute(
        select(MaterialParseJobModel.material_id, MaterialParseJobModel.id)
        .where(MaterialParseJobModel.material_id.in_(material_ids))
        .order_by(MaterialParseJobModel.started_at.desc())
    ).all()
    result: dict[str, str] = {}
    for material_id, job_id in rows:
        result.setdefault(material_id, job_id)
    return result
