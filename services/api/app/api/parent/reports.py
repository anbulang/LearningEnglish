from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    ParentAccountModel,
    PracticeSessionModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
    WeeklyReportModel,
)
from app.models.contracts import (
    LearningAssetMastery,
    MaterialReportSummary,
    MaterialStatus,
    ReviewTaskStatus,
    SpeakingAttemptStatus,
    WeeklyReportResponse,
)
from app.services.shared.mappers import weekly_report_from_model

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly", response_model=WeeklyReportResponse)
def get_weekly_report(
    child_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> WeeklyReportResponse:
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == child_id,
            ChildProfileModel.parent_account_id == current_parent.id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == child_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    asset_mastery, material_summaries = _build_learning_asset_report(db, child_id)
    weekly_report = weekly_report_from_model(report).model_copy(
        update={
            "report_summary": _report_summary(
                asset_mastery=asset_mastery,
                material_summaries=material_summaries,
                completed_sessions=report.completed_sessions,
                speaking_attempts=report.speaking_attempts,
            ),
            "asset_mastery": asset_mastery,
            "material_summaries": material_summaries,
        }
    )
    return WeeklyReportResponse(report=weekly_report)


def _build_learning_asset_report(
    db: Session,
    child_id: str,
) -> tuple[list[LearningAssetMastery], list[MaterialReportSummary]]:
    materials = db.scalars(
        select(CourseMaterialModel)
        .where(
            CourseMaterialModel.child_id == child_id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
        .order_by(CourseMaterialModel.lesson_date.desc(), CourseMaterialModel.created_at.desc())
    ).all()
    material_ids = [material.id for material in materials]
    if not material_ids:
        return [], []

    tasks = db.scalars(
        select(ReviewTaskModel).where(
            ReviewTaskModel.child_id == child_id,
            ReviewTaskModel.material_id.in_(material_ids),
        )
    ).all()
    attempts = db.scalars(
        select(SpeakingAttemptModel).where(
            SpeakingAttemptModel.child_id == child_id,
            SpeakingAttemptModel.material_id.in_(material_ids),
            SpeakingAttemptModel.status == SpeakingAttemptStatus.scored.value,
        )
    ).all()
    sessions = db.scalars(select(PracticeSessionModel).where(PracticeSessionModel.child_id == child_id)).all()

    tasks_by_asset: dict[str, list[ReviewTaskModel]] = defaultdict(list)
    tasks_by_material: dict[str, list[ReviewTaskModel]] = defaultdict(list)
    for task in tasks:
        tasks_by_material[task.material_id].append(task)
        asset_id = _task_asset_id(task)
        if asset_id:
            tasks_by_asset[asset_id].append(task)

    attempts_by_asset: dict[str, list[SpeakingAttemptModel]] = defaultdict(list)
    attempts_by_material: dict[str, list[SpeakingAttemptModel]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_material[attempt.material_id].append(attempt)
        if attempt.learning_asset_id:
            attempts_by_asset[attempt.learning_asset_id].append(attempt)

    weak_points = [_clean_text(point) for session in sessions for point in (session.weak_points or [])]

    asset_mastery: list[LearningAssetMastery] = []
    material_summaries: list[MaterialReportSummary] = []
    for material in materials:
        assets = [item for item in (material.learning_assets or []) if isinstance(item, dict)]
        material_tasks = tasks_by_material.get(material.id, [])
        material_attempts = attempts_by_material.get(material.id, [])
        material_summaries.append(
            MaterialReportSummary(
                material_id=material.id,
                title=material.title,
                topic=material.topic,
                asset_count=len(assets),
                completed_review_tasks=_completed_task_count(material_tasks),
                pending_review_tasks=_pending_task_count(material_tasks),
                speaking_attempts=len(material_attempts),
                average_speaking_score=_average_score(material_attempts),
            )
        )
        for asset in assets:
            asset_id = _clean_text(asset.get("id"))
            text = _clean_text(asset.get("text"))
            if not asset_id or not text:
                continue
            asset_tasks = tasks_by_asset.get(asset_id, [])
            asset_attempts = attempts_by_asset.get(asset_id, [])
            asset_weak_points = _weak_points_for_asset(text, weak_points)
            completed_tasks = _completed_task_count(asset_tasks)
            pending_tasks = _pending_task_count(asset_tasks)
            scores = _speaking_scores(asset_attempts)
            mastery_score = _mastery_score(
                review_attempts=len(asset_tasks),
                completed_review_tasks=completed_tasks,
                speaking_scores=scores,
                weak_points=asset_weak_points,
            )
            asset_mastery.append(
                LearningAssetMastery(
                    asset_id=asset_id,
                    material_id=material.id,
                    material_title=material.title,
                    text=text,
                    kind=_clean_text(asset.get("kind")) or "word",
                    translation=_clean_text(asset.get("translation")),
                    image_url=_clean_text(asset.get("generated_image_url")),
                    audio_url=_asset_audio_url(asset),
                    mastery_score=mastery_score,
                    mastery_status=_mastery_status(mastery_score),
                    review_attempts=len(asset_tasks),
                    completed_review_tasks=completed_tasks,
                    pending_review_tasks=pending_tasks,
                    speaking_attempts=len(asset_attempts),
                    best_speaking_score=max(scores) if scores else None,
                    last_speaking_score=scores[-1] if scores else None,
                    weak_points=asset_weak_points,
                    recommended_action=_recommended_action(
                        mastery_score=mastery_score,
                        pending_review_tasks=pending_tasks,
                        speaking_attempts=len(asset_attempts),
                    ),
                )
            )
    return asset_mastery, material_summaries


def _task_asset_id(task: ReviewTaskModel) -> str:
    content = task.content_json or {}
    value = content.get("asset_id") if isinstance(content, dict) else None
    return value.strip() if isinstance(value, str) else ""


def _completed_task_count(tasks: list[ReviewTaskModel]) -> int:
    return sum(1 for task in tasks if task.status == ReviewTaskStatus.completed.value)


def _pending_task_count(tasks: list[ReviewTaskModel]) -> int:
    return sum(1 for task in tasks if task.status != ReviewTaskStatus.completed.value)


def _average_score(attempts: list[SpeakingAttemptModel]) -> float | None:
    scores = _speaking_scores(attempts)
    return round(mean(scores), 1) if scores else None


def _speaking_scores(attempts: list[SpeakingAttemptModel]) -> list[float]:
    scores: list[float] = []
    for attempt in attempts:
        if attempt.overall_score is not None:
            scores.append(float(attempt.overall_score))
        elif attempt.pronunciation_score is not None:
            score = float(attempt.pronunciation_score)
            scores.append(score * 100 if score <= 1 else score)
    return scores


def _mastery_score(
    *,
    review_attempts: int,
    completed_review_tasks: int,
    speaking_scores: list[float],
    weak_points: list[str],
) -> float:
    review_ratio = completed_review_tasks / review_attempts if review_attempts else 0
    speaking_ratio = (mean(speaking_scores) / 100) if speaking_scores else 0
    score = 45 + 35 * review_ratio + 20 * speaking_ratio
    if weak_points:
        score -= 25
    return round(max(0.0, min(100.0, score)), 1)


def _mastery_status(score: float) -> str:
    if score >= 85:
        return "mastered"
    if score >= 60:
        return "progressing"
    return "needs_practice"


def _recommended_action(*, mastery_score: float, pending_review_tasks: int, speaking_attempts: int) -> str:
    if mastery_score < 60:
        return "先听标准音，再看图跟读 3 遍。"
    if pending_review_tasks:
        return "完成待复习任务，巩固本周重点。"
    if speaking_attempts == 0:
        return "补一次口语跟读，确认发音稳定。"
    return "保持当前节奏，下一次复习时快速过一遍。"


def _weak_points_for_asset(text: str, weak_points: list[str]) -> list[str]:
    normalized_text = _normalize_text(text)
    if " " not in normalized_text:
        matches = [point for point in weak_points if _normalize_text(point) == normalized_text]
    else:
        matches = [
            point
            for point in weak_points
            if point
            and (
                _normalize_text(point) == normalized_text
                or _normalize_text(point) in normalized_text
                or normalized_text in _normalize_text(point)
            )
        ]
    return list(dict.fromkeys(matches))


def _asset_audio_url(asset: dict[str, Any]) -> str:
    primary_accent = _clean_text(asset.get("primary_accent"))
    if primary_accent == "uk":
        return _clean_text(asset.get("tts_uk_url")) or _clean_text(asset.get("tts_us_url"))
    return _clean_text(asset.get("tts_us_url")) or _clean_text(asset.get("tts_uk_url"))


def _report_summary(
    *,
    asset_mastery: list[LearningAssetMastery],
    material_summaries: list[MaterialReportSummary],
    completed_sessions: int,
    speaking_attempts: int,
) -> str:
    mastered = sum(1 for item in asset_mastery if item.mastery_status == "mastered")
    needs_practice = sum(1 for item in asset_mastery if item.mastery_status == "needs_practice")
    return (
        f"本周覆盖 {len(material_summaries)} 份讲义、{len(asset_mastery)} 个学习资产；"
        f"已掌握 {mastered} 个，需加强 {needs_practice} 个；"
        f"完成 {completed_sessions} 次复习、{speaking_attempts} 次口语练习。"
    )


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_text(value: Any) -> str:
    return _clean_text(value).lower()
