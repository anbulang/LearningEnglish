"""Seed the authored phonics curriculum into the database (idempotent).

Reads app/content/phonics/*.json, upserts sound cards + units by their stable
ids, then either enqueues per-unit media generation (default) or generates the
TTS audio inline (--inline-media, for local/offline dev without Celery).

Usage:
    .venv/bin/python -m scripts.seed_phonics
    .venv/bin/python -m scripts.seed_phonics --inline-media
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.db.models import PhonicsSoundCardModel, PhonicsUnitModel  # noqa: E402
from app.services.shared.media_queue import enqueue_phonics_unit_media_job  # noqa: E402
from app.services.shared.phonics_content import clear_content_cache, load_sound_cards, load_units  # noqa: E402
from app.services.shared.phonics_media import generate_phonics_unit_media  # noqa: E402


def seed_sound_cards(db) -> int:
    cards = load_sound_cards()
    count = 0
    for card in cards.values():
        row = db.get(PhonicsSoundCardModel, card.id)
        if row is None:
            row = PhonicsSoundCardModel(id=card.id)
            db.add(row)
        row.card_type = card.card_type
        row.letter = card.letter
        row.phoneme = card.phoneme
        row.keyword = card.keyword
        row.keyword_cn = card.keyword_cn
        row.articulation_cue = card.articulation_cue
        row.common_spellings = list(card.common_spellings)
        row.speakable_sound = card.speakable_sound
        row.example_words = [w for w in card.example_words]
        count += 1
    db.commit()
    return count


def seed_units(db) -> list[str]:
    units = load_units()
    unit_ids: list[str] = []
    for unit in units:
        row = db.get(PhonicsUnitModel, unit.unit_id)
        content_changed = row is None or row.content_version != unit.content_version
        if row is None:
            row = PhonicsUnitModel(id=unit.unit_id)
            db.add(row)
        row.unit_code = unit.unit_code
        row.sequence_order = unit.sequence_order
        row.title = unit.title
        row.subtitle = unit.subtitle
        row.level = unit.level
        row.content_version = unit.content_version
        row.content_json = unit.model_dump()
        if content_changed:
            # content changed → drop stale media so it regenerates
            row.media_json = {}
            row.media_status = "pending"
        unit_ids.append(unit.unit_id)
    db.commit()
    return unit_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed phonics curriculum")
    parser.add_argument("--inline-media", action="store_true", help="Generate TTS audio synchronously (no Celery)")
    args = parser.parse_args()

    clear_content_cache()
    db = SessionLocal()
    try:
        card_count = seed_sound_cards(db)
        unit_ids = seed_units(db)
        print(f"seeded {card_count} sound cards, {len(unit_ids)} units")
        for unit_id in unit_ids:
            if args.inline_media:
                result = generate_phonics_unit_media(db, unit_id)
                print(f"  media {unit_id}: {result.get('status')}")
            else:
                enqueue_phonics_unit_media_job(unit_id)
                print(f"  enqueued media {unit_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
