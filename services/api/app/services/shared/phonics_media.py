"""Generate per-sound and per-word TTS audio for phonics units.

Reuses the shared media provider bundle (same DashScope/mock path as worksheet
media). Runs once at seed time (or via the phonics.process_unit_media worker),
never per child — phonics content is shared across all learners. Audio for the
sound cards is written to their columns; audio for a unit's words / sentences /
heart words is written to the unit's ``media_json`` so it survives a content
re-seed of ``content_json``.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PhonicsSoundCardModel, PhonicsUnitModel, StoredAssetModel
from app.models.contracts import MediaGenerationStatus
from app.services.shared.learning_asset_media import (
    MediaProviderConfigurationError,
    build_media_provider_bundle,
)
from app.services.shared.storage import get_storage_service

logger = logging.getLogger(__name__)

_ACCENTS = ("us", "uk")  # generate both; the API serves the child's chosen accent


def _save_or_upsert(db: Session, storage, *, object_key: str, content_type: str, payload: bytes) -> StoredAssetModel:
    saved = storage.save_bytes(
        owner_type="phonics_media",
        owner_id="phonics",
        object_key=object_key,
        content_type=content_type,
        payload=payload,
    )
    existing = db.scalar(select(StoredAssetModel).where(StoredAssetModel.object_key == saved.object_key))
    if existing is None:
        db.add(saved)
        return saved
    existing.owner_type = saved.owner_type
    existing.owner_id = saved.owner_id
    existing.bucket = saved.bucket
    existing.content_type = saved.content_type
    existing.size_bytes = saved.size_bytes
    existing.url = saved.url
    db.add(existing)
    return existing


def _synthesize(bundle, db, storage, *, text: str, object_key_stem: str, accent: str) -> tuple[str, str]:
    """Return (audio_url, status). Best-effort — never raises."""
    clean = (text or "").strip()
    if not clean:
        return "", MediaGenerationStatus.failed.value
    try:
        generated = bundle.tts_provider.synthesize(clean, accent)
        extension = generated.extension if generated.extension.startswith(".") else f".{generated.extension}"
        asset = _save_or_upsert(
            db,
            storage,
            object_key=f"{object_key_stem}{extension}",
            content_type=generated.content_type,
            payload=generated.payload,
        )
        return asset.url, MediaGenerationStatus.ready.value
    except Exception as exc:  # pragma: no cover - provider surface
        logger.warning("phonics tts failed for %s: %s", object_key_stem, exc)
        return "", MediaGenerationStatus.failed.value


def _statuses_ready(statuses: list[str]) -> str:
    if statuses and all(s == MediaGenerationStatus.ready.value for s in statuses):
        return MediaGenerationStatus.ready.value
    if any(s == MediaGenerationStatus.ready.value for s in statuses):
        return "partial"
    return MediaGenerationStatus.failed.value


def generate_phonics_unit_media(db: Session, unit_id: str) -> dict[str, str]:
    """Generate audio for one unit and its referenced sound cards."""
    unit = db.get(PhonicsUnitModel, unit_id)
    if unit is None:
        return {"unit_id": unit_id, "status": "missing"}

    try:
        bundle = build_media_provider_bundle()
    except MediaProviderConfigurationError:
        unit.media_status = MediaGenerationStatus.failed.value
        db.add(unit)
        db.commit()
        return {"unit_id": unit_id, "status": "config_failed"}

    storage = get_storage_service()
    statuses: list[str] = []
    try:
        content = dict(unit.content_json or {})
        # Accumulate per-card audio across accents so a card touched by several
        # units keeps both accents; media_json is nested {accent: {words,...}}.
        card_variants: dict[str, dict] = {}
        media_by_accent: dict[str, dict] = {}

        for accent in _ACCENTS:
            # 1) sound cards (sound + keyword), shared across units.
            for card_id in content.get("sound_card_ids", []):
                card = db.get(PhonicsSoundCardModel, card_id)
                if card is None:
                    continue
                sound_url, sound_status = _synthesize(
                    bundle, db, storage,
                    text=card.speakable_sound,
                    object_key_stem=f"generated/media/phonics/cards/{card.id}/sound-{accent}",
                    accent=accent,
                )
                key_url, key_status = _synthesize(
                    bundle, db, storage,
                    text=card.keyword,
                    object_key_stem=f"generated/media/phonics/cards/{card.id}/keyword-{accent}",
                    accent=accent,
                )
                variants = dict(card.audio_variants or {})
                variants[accent] = {
                    "sound_url": sound_url,
                    "sound_status": sound_status,
                    "keyword_url": key_url,
                    "keyword_status": key_status,
                }
                card.audio_variants = variants
                card_variants[card.id] = variants
                if accent == "us":
                    # keep the flat columns as the us canonical (back-compat)
                    card.sound_audio_url = sound_url or card.sound_audio_url
                    card.sound_tts_status = sound_status
                    card.keyword_audio_url = key_url or card.keyword_audio_url
                    card.keyword_tts_status = key_status
                db.add(card)
                statuses += [sound_status, key_status]

            media: dict[str, dict] = {"words": {}, "sentences": {}, "heart_words": {}}

            # 2) decodable words.
            for word in content.get("decodable_words", []):
                url, st = _synthesize(
                    bundle, db, storage,
                    text=word.get("text", ""),
                    object_key_stem=f"generated/media/phonics/units/{unit.id}/words/{word.get('id')}-{accent}",
                    accent=accent,
                )
                media["words"][word.get("id")] = {"audio_url": url, "status": st}
                statuses.append(st)

            # 3) sentences.
            for sentence in content.get("sentences", []):
                url, st = _synthesize(
                    bundle, db, storage,
                    text=sentence.get("text", ""),
                    object_key_stem=f"generated/media/phonics/units/{unit.id}/sentences/{sentence.get('id')}-{accent}",
                    accent=accent,
                )
                media["sentences"][sentence.get("id")] = {"audio_url": url, "status": st}
                statuses.append(st)

            # 4) heart words (keyed by text).
            for idx, heart in enumerate(content.get("heart_words", [])):
                text = heart.get("text", "")
                url, st = _synthesize(
                    bundle, db, storage,
                    text=text,
                    object_key_stem=f"generated/media/phonics/units/{unit.id}/heart/{idx}-{accent}",
                    accent=accent,
                )
                media["heart_words"][text] = {"audio_url": url, "status": st}
                statuses.append(st)

            media_by_accent[accent] = media

        unit.media_json = media_by_accent
        unit.media_status = _statuses_ready(statuses)
        db.add(unit)
        db.commit()
        return {"unit_id": unit_id, "status": unit.media_status}
    finally:
        close = getattr(bundle, "close", None)
        if callable(close):
            close()
