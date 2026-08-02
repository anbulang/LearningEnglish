"""SM-2 spaced-repetition scheduling for review tasks.

A binary-quality variant of the classic SM-2 algorithm: each review is either
correct (remembered) or not. Correct answers grow the interval geometrically by
the ease factor; a miss resets the task to be seen again the next day. Pure and
deterministic — no fabricated state.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 2.7
EASE_UP = 0.1     # ease bonus on a correct recall
EASE_DOWN = 0.2   # ease penalty on a miss
FIRST_INTERVAL = 1
SECOND_INTERVAL = 6


@dataclass(frozen=True)
class ScheduleResult:
    repetitions: int
    ease_factor: float
    interval_days: int


def sm2_schedule(
    *,
    correct: bool,
    repetitions: int,
    ease_factor: float,
    interval_days: int,
) -> ScheduleResult:
    """Return the next (repetitions, ease_factor, interval_days) for a task.

    - miss: streak resets to 0, ease drops (floored at 1.3), review again in 1 day.
    - hit:  streak +1; interval is 1 day (1st), 6 days (2nd), then prev*ease;
      ease rises slightly (capped at 2.7).
    """
    ef = ease_factor if ease_factor and ease_factor > 0 else DEFAULT_EASE

    if not correct:
        return ScheduleResult(repetitions=0, ease_factor=max(MIN_EASE, round(ef - EASE_DOWN, 3)), interval_days=FIRST_INTERVAL)

    reps = (repetitions or 0) + 1
    ef = min(MAX_EASE, round(ef + EASE_UP, 3))
    if reps == 1:
        interval = FIRST_INTERVAL
    elif reps == 2:
        interval = SECOND_INTERVAL
    else:
        interval = max(1, round((interval_days or SECOND_INTERVAL) * ef))
    return ScheduleResult(repetitions=reps, ease_factor=ef, interval_days=interval)
