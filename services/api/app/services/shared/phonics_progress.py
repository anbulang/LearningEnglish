"""Per-child phonics mastery updates — shared by the parent API and the worker.

Kept in ``services/shared`` so the async ASR scoring worker can update mastery
without importing HTTP route packages (enforced by test_engineering_boundaries).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ChildPhonicsProgressModel, PhonicsAttemptModel, PhonicsUnitModel
from app.models.contracts import PhonicsPracticeType
from app.services.shared.phonics_scoring import decide_mastery


def get_or_create_progress(db: Session, child_id: str, unit_id: str) -> ChildPhonicsProgressModel:
    stmt = select(ChildPhonicsProgressModel).where(
        ChildPhonicsProgressModel.child_id == child_id,
        ChildPhonicsProgressModel.unit_id == unit_id,
    )
    progress = db.scalar(stmt)
    if progress is not None:
        return progress
    # Create inside a SAVEPOINT so a concurrent creator racing the
    # (child_id, unit_id) unique constraint rolls back just this INSERT (not the
    # caller's pending attempt row) — then reuse the row the winner created
    # instead of surfacing a 500.
    progress = ChildPhonicsProgressModel(child_id=child_id, unit_id=unit_id, status="unlocked")
    try:
        with db.begin_nested():
            db.add(progress)
            db.flush()
    except IntegrityError:
        progress = db.scalar(stmt)
        if progress is None:
            raise
    return progress


def _total_blend_targets(unit: PhonicsUnitModel) -> int:
    content = unit.content_json or {}
    for step in content.get("steps", []):
        if step.get("practice_type") == PhonicsPracticeType.blend_word_asr.value:
            return len(step.get("word_ids", []))
    return len(content.get("decodable_words", []))


def apply_attempt_to_progress(
    db: Session,
    *,
    unit: PhonicsUnitModel,
    attempt: PhonicsAttemptModel,
) -> ChildPhonicsProgressModel:
    """Fold one scored attempt into the child's unit progress and re-decide mastery."""
    progress = get_or_create_progress(db, attempt.child_id, unit.id)
    progress.attempts_count = (progress.attempts_count or 0) + 1
    progress.last_attempt_at = datetime.now(timezone.utc)

    if attempt.practice_type == PhonicsPracticeType.first_sound_tap.value and attempt.accuracy_score is not None:
        progress.first_sound_accuracy = max(progress.first_sound_accuracy or 0.0, attempt.accuracy_score)

    if attempt.practice_type == PhonicsPracticeType.blend_word_asr.value and attempt.passed:
        word = (attempt.target_text or "").strip().lower()
        if word:
            blended = list(progress.blended_words or [])
            if word not in blended:
                blended.append(word)
            progress.blended_words = blended
            scores = dict(progress.grapheme_scores or {})
            for letter in word:
                if letter.isalpha():
                    scores[letter] = max(scores.get(letter, 0.0), attempt.accuracy_score or 1.0)
            progress.grapheme_scores = scores

    # Tile-build (搭词) and dictation (听写) are tap-based encoding tasks: every word
    # the child assembles correctly is decoding evidence, so it counts toward the
    # same blended-words set that gates mastery (and lets a no-mic child progress).
    if attempt.practice_type in (
        PhonicsPracticeType.tile_build.value,
        PhonicsPracticeType.dictation.value,
    ):
        blended = list(progress.blended_words or [])
        for item in (attempt.item_results or []):
            if not item.get("correct"):
                continue
            word = (item.get("prompt") or "").strip().lower()
            if word and word not in blended:
                blended.append(word)
        progress.blended_words = blended

    decision = decide_mastery(
        first_sound_accuracy=progress.first_sound_accuracy or 0.0,
        blended_words=list(progress.blended_words or []),
        total_blend_targets=_total_blend_targets(unit),
        attempts_count=progress.attempts_count or 0,
    )
    progress.decoding_accuracy = decision.decoding_accuracy
    # never demote a mastered unit
    if progress.status != "mastered":
        progress.status = decision.status
    if decision.mastered and progress.mastered_at is None:
        progress.mastered_at = datetime.now(timezone.utc)
        progress.status = "mastered"
    db.add(progress)
    return progress
