"""Deterministic scoring for review practice tasks — no fabricated scores.

The child's answer is checked against the task's authored ``content_json`` (which
carries the correct answer), so a PracticeSession's score and weak points reflect
what actually happened instead of a hard-coded value. Mirrors the honest,
LLM-free approach used by ``phonics_scoring``.
"""

from __future__ import annotations


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def score_review_task(
    *,
    task_type: str,
    content: dict,
    answer: str = "",
    answers: list[str] | None = None,
) -> tuple[bool, str]:
    """Return ``(correct, item)``.

    ``item`` is the vocabulary word / prompt this task exercises; the caller logs
    it as a weak point when ``correct`` is False.
    """
    content = content or {}
    answers = answers or []

    if task_type == "listen_choice":
        target = content.get("correct_answer", "")
        correct = bool(target) and _norm(answer) == _norm(target)
        return correct, target or content.get("prompt", "")

    if task_type == "match_choice":
        right = [str(x) for x in content.get("right", [])]
        correct = (
            len(right) > 0
            and len(answers) == len(right)
            and all(_norm(a) == _norm(b) for a, b in zip(answers, right))
        )
        left = content.get("left") or []
        item = (str(left[0]) if left else "") or content.get("prompt", "")
        return correct, item

    if task_type == "flashcard":
        # read-aloud recognition has no objective key → honest self-rate
        correct = _norm(answer) in {"known", "good", "easy"}
        return correct, content.get("word", "") or content.get("prompt", "")

    # speaking_prompt / parent_coaching / unknown: seen, not scored against a key
    return True, ""


def score_review_session(scored: list[tuple[bool, str]]) -> tuple[float, list[str]]:
    """Aggregate per-task ``(correct, item)`` into (score 0-100, deduped weak_points)."""
    total = len(scored)
    if total == 0:
        return 0.0, []
    correct = sum(1 for ok, _ in scored if ok)
    score = round(100.0 * correct / total, 1)
    weak = [item for ok, item in scored if not ok and item]
    # dedupe, preserve order
    weak = list(dict.fromkeys(weak))
    return score, weak
