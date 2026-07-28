"""Deterministic phonics scoring — no LLM text-judge, no fabricated numbers.

For a known single target word, ASR is at its most reliable, so we score the
transcript against the *expected* word with normalized string similarity. Tap
interactions are scored by simple correctness counting. Mastery is a composite
gate over first-sound accuracy and the set of words the child has blended.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Mastery thresholds (Blevins: decoding accuracy + rule application).
WORD_PASS_THRESHOLD = 0.8
FIRST_SOUND_MASTERY_THRESHOLD = 0.8
MIN_BLENDED_WORDS_FOR_MASTERY = 3

_WORD_RE = re.compile(r"[^a-z]+")


def _normalize(value: str) -> str:
    return _WORD_RE.sub(" ", (value or "").strip().lower()).strip()


@dataclass
class WordMatchResult:
    passed: bool
    accuracy: float
    status: str  # "scored" | "no_match"
    feedback: str


def score_word_match(transcript: str, target_text: str) -> WordMatchResult:
    """Score a spoken single word against the expected target."""
    target = _normalize(target_text)
    heard = _normalize(transcript)
    if not target:
        return WordMatchResult(True, 1.0, "scored", "很棒！")
    if not heard:
        return WordMatchResult(False, 0.0, "no_match", "没有听清你的声音，再试一次吧。")

    tokens = heard.split()
    if target in tokens:
        return WordMatchResult(True, 1.0, "scored", "读得很准！")

    best = max((SequenceMatcher(None, target, token).ratio() for token in tokens), default=0.0)
    # also compare against the whole heard string in case ASR merged the word
    best = max(best, SequenceMatcher(None, target, heard).ratio())
    accuracy = round(best, 3)
    if accuracy >= WORD_PASS_THRESHOLD:
        return WordMatchResult(True, accuracy, "scored", "读得不错！")
    return WordMatchResult(
        False,
        accuracy,
        "scored",
        f"再听一遍，把每个音连起来读：{target_text}。",
    )


@dataclass
class TapScore:
    accuracy: float
    passed: bool
    correct: int
    total: int


def asr_accent_for(child_accent: str, *, default: str = "am") -> str:
    """Map a child's phonics accent (us|uk) to the speech-scorer accent label.

    The accent is a free-form hint fed to the scoring model ("am" American /
    "br" British), so a British child's read-aloud is judged against a British
    reference. Unknown/us falls back to the configured default (American).
    """
    return "br" if (child_accent or "").strip().lower() == "uk" else default


def score_tap_items(item_results: list[dict]) -> TapScore:
    """Score a batch of tap/choice items by correctness count."""
    total = len(item_results)
    correct = sum(1 for item in item_results if item.get("correct"))
    accuracy = round(correct / total, 3) if total else 0.0
    return TapScore(accuracy=accuracy, passed=accuracy >= FIRST_SOUND_MASTERY_THRESHOLD, correct=correct, total=total)


@dataclass
class MasteryDecision:
    status: str  # unlocked | in_progress | mastered
    mastered: bool
    decoding_accuracy: float
    reasons: list[str] = field(default_factory=list)


def decide_mastery(
    *,
    first_sound_accuracy: float,
    blended_words: list[str],
    total_blend_targets: int,
    attempts_count: int,
) -> MasteryDecision:
    required = min(MIN_BLENDED_WORDS_FOR_MASTERY, total_blend_targets) if total_blend_targets else MIN_BLENDED_WORDS_FOR_MASTERY
    blended_count = len(set(blended_words))
    # Composite decoding signal shown to parents: blend the two axes we measure.
    blend_ratio = (blended_count / required) if required else 0.0
    decoding_accuracy = round(min(1.0, 0.5 * min(1.0, blend_ratio) + 0.5 * min(1.0, first_sound_accuracy)), 3)

    reasons: list[str] = []
    sound_ok = first_sound_accuracy >= FIRST_SOUND_MASTERY_THRESHOLD
    blend_ok = blended_count >= required
    if not sound_ok:
        reasons.append("圈首音正确率还不够（需 ≥80%）。")
    if not blend_ok:
        reasons.append(f"已拼读 {blended_count}/{required} 个单词。")

    if sound_ok and blend_ok:
        return MasteryDecision("mastered", True, decoding_accuracy, ["已达标，解锁下一课。"])
    if attempts_count > 0:
        return MasteryDecision("in_progress", False, decoding_accuracy, reasons)
    return MasteryDecision("unlocked", False, decoding_accuracy, reasons)
