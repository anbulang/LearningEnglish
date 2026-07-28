"""Parent-side phonics orchestration: resolve authored units + per-child
progress into API responses, and record practice attempts."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChildPhonicsProgressModel,
    ChildProfileModel,
    PhonicsAttemptModel,
    PhonicsSoundCardModel,
    PhonicsUnitModel,
)
from app.models.contracts import (
    MediaGenerationStatus,
    PhonicsAttempt,
    PhonicsAttemptResponse,
    PhonicsCourseInfo,
    PhonicsExampleWord,
    PhonicsFirstSoundItem,
    PhonicsHeartWord,
    PhonicsLessonStep,
    PhonicsPracticeType,
    PhonicsProgressResponse,
    PhonicsSentence,
    PhonicsSoundCard,
    PhonicsTapAttemptCreate,
    PhonicsUnitDetail,
    PhonicsUnitDetailResponse,
    PhonicsUnitListResponse,
    PhonicsUnitProgress,
    PhonicsUnitStatus,
    PhonicsUnitSummary,
)
from app.services.shared.mappers import phonics_attempt_from_model
from app.services.shared.phonics_content import load_scope
from app.services.shared.phonics_progress import apply_attempt_to_progress, get_or_create_progress
from app.services.shared.phonics_scoring import score_tap_items


def _course_info() -> PhonicsCourseInfo:
    course = load_scope().course
    return PhonicsCourseInfo(id=course.id, title=course.title, description=course.description)


def _media_status(value: str) -> MediaGenerationStatus:
    try:
        return MediaGenerationStatus(value)
    except ValueError:
        return MediaGenerationStatus.pending


def _progress_contract(unit_id: str, progress: ChildPhonicsProgressModel | None) -> PhonicsUnitProgress:
    if progress is None:
        return PhonicsUnitProgress(unit_id=unit_id, status=PhonicsUnitStatus.unlocked)
    return PhonicsUnitProgress(
        unit_id=unit_id,
        status=PhonicsUnitStatus(progress.status) if progress.status else PhonicsUnitStatus.unlocked,
        decoding_accuracy=progress.decoding_accuracy or 0.0,
        first_sound_accuracy=progress.first_sound_accuracy or 0.0,
        grapheme_scores=dict(progress.grapheme_scores or {}),
        attempts_count=progress.attempts_count or 0,
        blended_words=list(progress.blended_words or []),
        mastered=progress.status == "mastered",
    )


def _load_progress_map(db: Session, child_id: str) -> dict[str, ChildPhonicsProgressModel]:
    rows = db.scalars(
        select(ChildPhonicsProgressModel).where(ChildPhonicsProgressModel.child_id == child_id)
    ).all()
    return {row.unit_id: row for row in rows}


def _effective_status(index: int, unit_id: str, units: list[PhonicsUnitModel], progress_map: dict) -> PhonicsUnitStatus:
    progress = progress_map.get(unit_id)
    if progress is not None and progress.status == "mastered":
        return PhonicsUnitStatus.mastered
    if progress is not None and progress.status == "in_progress":
        return PhonicsUnitStatus.in_progress
    if index == 0:
        return PhonicsUnitStatus.unlocked
    prev = progress_map.get(units[index - 1].id)
    if prev is not None and prev.status == "mastered":
        return PhonicsUnitStatus.unlocked
    return PhonicsUnitStatus.locked


def list_units(db: Session, child_id: str) -> PhonicsUnitListResponse:
    units = db.scalars(select(PhonicsUnitModel).order_by(PhonicsUnitModel.sequence_order)).all()
    progress_map = _load_progress_map(db, child_id)
    summaries: list[PhonicsUnitSummary] = []
    next_unit_id = ""
    for index, unit in enumerate(units):
        status = _effective_status(index, unit.id, units, progress_map)
        progress = progress_map.get(unit.id)
        summaries.append(
            PhonicsUnitSummary(
                id=unit.id,
                unit_code=unit.unit_code,
                sequence_order=unit.sequence_order,
                title=unit.title,
                subtitle=unit.subtitle,
                level=unit.level,
                media_status=_media_status(unit.media_status),
                status=status,
                decoding_accuracy=(progress.decoding_accuracy if progress else 0.0) or 0.0,
            )
        )
        if not next_unit_id and status in (PhonicsUnitStatus.unlocked, PhonicsUnitStatus.in_progress):
            next_unit_id = unit.id
    return PhonicsUnitListResponse(course=_course_info(), units=summaries, next_unit_id=next_unit_id)


def _child_accent(db: Session, child_id: str) -> str:
    child = db.get(ChildProfileModel, child_id)
    accent = (child.accent if child is not None else "us") or "us"
    return accent if accent in {"us", "uk"} else "us"


def _accent_media(media_json: dict | None, accent: str) -> dict:
    """Return the {words, sentences, heart_words} bucket for the accent.

    Handles both the new accent-nested shape ({"us": {...}, "uk": {...}}) and the
    legacy flat shape ({"words": {...}, ...}) for forward/backward compatibility.
    """
    media = media_json or {}
    if isinstance(media.get(accent), dict):
        return media[accent]
    if isinstance(media.get("us"), dict):
        return media["us"]
    return media


def _resolve_sound_cards(db: Session, card_ids: list[str], accent: str) -> list[PhonicsSoundCard]:
    cards = []
    for card_id in card_ids:
        card = db.get(PhonicsSoundCardModel, card_id)
        if card is None:
            continue
        variants = card.audio_variants or {}
        variant = variants.get(accent) or variants.get("us") or {}
        cards.append(
            PhonicsSoundCard(
                id=card.id,
                card_type=card.card_type,
                letter=card.letter,
                phoneme=card.phoneme,
                keyword=card.keyword,
                keyword_cn=card.keyword_cn,
                articulation_cue=card.articulation_cue,
                common_spellings=list(card.common_spellings or []),
                speakable_sound=card.speakable_sound,
                example_words=[PhonicsExampleWord(**w) for w in (card.example_words or [])],
                sound_audio_url=variant.get("sound_url") or card.sound_audio_url,
                sound_tts_status=_media_status(variant.get("sound_status") or card.sound_tts_status),
                keyword_audio_url=variant.get("keyword_url") or card.keyword_audio_url,
                keyword_tts_status=_media_status(variant.get("keyword_status") or card.keyword_tts_status),
            )
        )
    return cards


def get_unit_detail(db: Session, child_id: str, unit_id: str) -> PhonicsUnitDetailResponse | None:
    unit = db.get(PhonicsUnitModel, unit_id)
    if unit is None:
        return None
    content = unit.content_json or {}
    accent = _child_accent(db, child_id)
    media = _accent_media(unit.media_json, accent)
    word_media = media.get("words", {})
    sentence_media = media.get("sentences", {})
    heart_media = media.get("heart_words", {})

    words = {}
    from app.models.contracts import PhonicsWord

    decodable = []
    for w in content.get("decodable_words", []):
        m = word_media.get(w.get("id"), {})
        word = PhonicsWord(
            id=w.get("id"),
            text=w.get("text", ""),
            segments=list(w.get("segments", [])),
            cn=w.get("cn", ""),
            kind=w.get("kind", "real"),
            audio_url=m.get("audio_url", ""),
            tts_status=_media_status(m.get("status", "pending")),
        )
        decodable.append(word)
        words[word.id] = word

    sentences = [
        PhonicsSentence(
            id=s.get("id"),
            text=s.get("text", ""),
            cn=s.get("cn", ""),
            audio_url=sentence_media.get(s.get("id"), {}).get("audio_url", ""),
            tts_status=_media_status(sentence_media.get(s.get("id"), {}).get("status", "pending")),
        )
        for s in content.get("sentences", [])
    ]

    heart_words = [
        PhonicsHeartWord(
            text=h.get("text", ""),
            cn=h.get("cn", ""),
            audio_url=heart_media.get(h.get("text", ""), {}).get("audio_url", ""),
            tts_status=_media_status(heart_media.get(h.get("text", ""), {}).get("status", "pending")),
        )
        for h in content.get("heart_words", [])
    ]

    first_sound_items = []
    for item in content.get("first_sound_items", []):
        word = words.get(item.get("word_id"))
        first_sound_items.append(
            PhonicsFirstSoundItem(
                id=item.get("id"),
                word_id=item.get("word_id"),
                text=word.text if word else "",
                cn=word.cn if word else "",
                answer=item.get("answer", ""),
                options=list(item.get("options", [])),
                audio_url=word.audio_url if word else "",
            )
        )

    steps = [
        PhonicsLessonStep(
            key=step.get("key", ""),
            practice_type=_practice_type(step.get("practice_type", "none")),
            title=step.get("title", ""),
            instruction=step.get("instruction", ""),
            card_ids=list(step.get("card_ids", [])),
            word_ids=list(step.get("word_ids", [])),
            item_ids=list(step.get("item_ids", [])),
            heart_words=list(step.get("heart_words", [])),
        )
        for step in content.get("steps", [])
    ]

    progress = db.scalar(
        select(ChildPhonicsProgressModel).where(
            ChildPhonicsProgressModel.child_id == child_id,
            ChildPhonicsProgressModel.unit_id == unit.id,
        )
    )

    return PhonicsUnitDetailResponse(
        unit=PhonicsUnitDetail(
            id=unit.id,
            unit_code=unit.unit_code,
            sequence_order=unit.sequence_order,
            title=unit.title,
            subtitle=unit.subtitle,
            level=unit.level,
            vowel_focus=content.get("vowel_focus", ""),
            letters=list(content.get("letters", [])),
            media_status=_media_status(unit.media_status),
        ),
        sound_cards=_resolve_sound_cards(db, content.get("sound_card_ids", []), accent),
        decodable_words=decodable,
        sentences=sentences,
        heart_words=heart_words,
        first_sound_items=first_sound_items,
        steps=steps,
        progress=_progress_contract(unit.id, progress),
    )


def _practice_type(value: str) -> PhonicsPracticeType:
    try:
        return PhonicsPracticeType(value)
    except ValueError:
        return PhonicsPracticeType.none


def record_tap_attempt(db: Session, child_id: str, payload: PhonicsTapAttemptCreate) -> PhonicsAttemptResponse | None:
    unit = db.get(PhonicsUnitModel, payload.unit_id)
    if unit is None:
        return None
    item_results = [item.model_dump() for item in payload.item_results]
    tap = score_tap_items(item_results)
    attempt = PhonicsAttemptModel(
        id=f"phattempt_{uuid4().hex[:12]}",
        child_id=child_id,
        unit_id=unit.id,
        step=payload.step,
        practice_type=payload.practice_type.value,
        target_text=payload.target_text,
        item_results=item_results,
        accuracy_score=tap.accuracy,
        passed=tap.passed,
        feedback=f"答对 {tap.correct}/{tap.total} 个。" if tap.total else "",
        status="scored",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()
    progress = apply_attempt_to_progress(db, unit=unit, attempt=attempt)
    db.commit()
    db.refresh(attempt)
    return PhonicsAttemptResponse(
        attempt=phonics_attempt_from_model(attempt),
        progress=_progress_contract(unit.id, progress),
    )


def get_progress(db: Session, child_id: str) -> PhonicsProgressResponse:
    units = db.scalars(select(PhonicsUnitModel).order_by(PhonicsUnitModel.sequence_order)).all()
    progress_map = _load_progress_map(db, child_id)
    unit_progress = []
    mastered = 0
    next_unit_id = ""
    for index, unit in enumerate(units):
        status = _effective_status(index, unit.id, units, progress_map)
        row = progress_map.get(unit.id)
        contract = _progress_contract(unit.id, row)
        contract.status = status
        unit_progress.append(contract)
        if status == PhonicsUnitStatus.mastered:
            mastered += 1
        if not next_unit_id and status in (PhonicsUnitStatus.unlocked, PhonicsUnitStatus.in_progress):
            next_unit_id = unit.id
    return PhonicsProgressResponse(
        course=_course_info(),
        units=unit_progress,
        next_unit_id=next_unit_id,
        mastered_count=mastered,
        total_units=len(units),
    )
