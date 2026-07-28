"""Load + validate the authored phonics curriculum (JSON in app/content/phonics).

The scope & sequence, sound-spelling cards and per-unit lessons are fixed,
git-versioned content — NOT AI-generated and NOT stored in a migration. This
module is the single source of truth for reading and validating that content;
the seeder (scripts/seed_phonics.py) upserts it into the database and the media
worker backfills the audio.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "phonics"


class SoundCardContent(BaseModel):
    id: str
    card_type: str = "consonant"
    letter: str = ""
    phoneme: str = ""
    keyword: str = ""
    keyword_cn: str = ""
    articulation_cue: str = ""
    common_spellings: list[str] = Field(default_factory=list)
    speakable_sound: str = ""
    example_words: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_speakable(self) -> "SoundCardContent":
        # A sound card must feed TTS a *speakable* description, never raw IPA —
        # the media worker rejects "/.../"-style notation.
        value = self.speakable_sound.strip()
        if value.startswith("/") or value.startswith("["):
            raise ValueError(f"sound card {self.id}: speakable_sound must not be phonetic notation")
        if not value:
            raise ValueError(f"sound card {self.id}: speakable_sound is required")
        return self


class WordContent(BaseModel):
    id: str
    text: str
    segments: list[str] = Field(default_factory=list)
    cn: str = ""
    kind: str = "real"


class SentenceContent(BaseModel):
    id: str
    text: str
    cn: str = ""


class HeartWordContent(BaseModel):
    text: str
    cn: str = ""


class FirstSoundItemContent(BaseModel):
    id: str
    word_id: str
    answer: str
    options: list[str] = Field(default_factory=list)


class LessonStepContent(BaseModel):
    key: str
    practice_type: str = "none"
    title: str = ""
    instruction: str = ""
    card_ids: list[str] = Field(default_factory=list)
    word_ids: list[str] = Field(default_factory=list)
    item_ids: list[str] = Field(default_factory=list)
    heart_words: list[str] = Field(default_factory=list)


class UnitContent(BaseModel):
    unit_id: str
    unit_code: str
    sequence_order: int
    level: str = "1"
    content_version: str = "1"
    title: str
    subtitle: str = ""
    vowel_focus: str = ""
    letters: list[str] = Field(default_factory=list)
    sound_card_ids: list[str] = Field(default_factory=list)
    heart_words: list[HeartWordContent] = Field(default_factory=list)
    decodable_words: list[WordContent] = Field(default_factory=list)
    sentences: list[SentenceContent] = Field(default_factory=list)
    first_sound_items: list[FirstSoundItemContent] = Field(default_factory=list)
    steps: list[LessonStepContent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_internal_refs(self) -> "UnitContent":
        word_ids = {w.id for w in self.decodable_words}
        for item in self.first_sound_items:
            if item.word_id not in word_ids:
                raise ValueError(f"unit {self.unit_code}: first_sound_item {item.id} references unknown word {item.word_id}")
            word = next(w for w in self.decodable_words if w.id == item.word_id)
            if word.segments and item.answer != word.segments[0]:
                raise ValueError(
                    f"unit {self.unit_code}: first_sound_item {item.id} answer '{item.answer}' "
                    f"does not match first segment of '{word.text}'"
                )
            if item.answer not in item.options:
                raise ValueError(f"unit {self.unit_code}: first_sound_item {item.id} answer not in options")
        item_ids = {i.id for i in self.first_sound_items}
        for step in self.steps:
            for wid in step.word_ids:
                if wid not in word_ids:
                    raise ValueError(f"unit {self.unit_code}: step {step.key} references unknown word {wid}")
            for iid in step.item_ids:
                if iid not in item_ids:
                    raise ValueError(f"unit {self.unit_code}: step {step.key} references unknown first_sound item {iid}")
        return self


class ScopeUnitEntry(BaseModel):
    unit_id: str
    unit_code: str
    sequence_order: int
    level: str = "1"
    title: str = ""
    file: str


class CourseInfo(BaseModel):
    id: str
    title: str
    description: str = ""


class ScopeAndSequence(BaseModel):
    version: str = "1"
    course: CourseInfo
    units: list[ScopeUnitEntry] = Field(default_factory=list)


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def load_scope() -> ScopeAndSequence:
    return ScopeAndSequence.model_validate(_read_json(CONTENT_DIR / "scope_and_sequence.json"))


@lru_cache(maxsize=1)
def load_sound_cards() -> dict[str, SoundCardContent]:
    raw = _read_json(CONTENT_DIR / "sound_cards.json")
    cards = [SoundCardContent.model_validate(item) for item in raw.get("cards", [])]
    return {card.id: card for card in cards}


@lru_cache(maxsize=1)
def load_units() -> list[UnitContent]:
    scope = load_scope()
    cards = load_sound_cards()
    units: list[UnitContent] = []
    for entry in sorted(scope.units, key=lambda e: e.sequence_order):
        unit = UnitContent.model_validate(_read_json(CONTENT_DIR / entry.file))
        for card_id in unit.sound_card_ids:
            if card_id not in cards:
                raise ValueError(f"unit {unit.unit_code}: references unknown sound card {card_id}")
        if unit.unit_id != entry.unit_id or unit.unit_code != entry.unit_code:
            raise ValueError(f"scope/unit mismatch for {entry.unit_code}")
        units.append(unit)
    return units


def clear_content_cache() -> None:
    load_scope.cache_clear()
    load_sound_cards.cache_clear()
    load_units.cache_clear()
