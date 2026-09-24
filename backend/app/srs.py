"""Simplified SM-2 scheduler with Anki-style grades (again/hard/good/easy).

- again: back to a 10-minute relearn step, ease −0.20 (a review card that
  fails counts as a lapse)
- hard:  interval × 1.2, ease −0.15 (learning cards repeat the current step)
- good:  1st success → 1 day, 2nd → 6 days (graduation), then interval × ease
- easy:  graduate immediately (4 days), then interval × ease × 1.3, ease +0.15

Ease is clamped to [1.3, 2.8].
"""

from __future__ import annotations

from datetime import timedelta

from app.models import Word, utcnow

MIN_EASE = 1.3
MAX_EASE = 2.8
RELEARN_STEP = timedelta(minutes=10)
RATINGS = ("again", "hard", "good", "easy")


def _clamp(ease: float) -> float:
    return max(MIN_EASE, min(MAX_EASE, ease))


def _schedule(
    ease: float, interval_days: float, reps: int, rating: str
) -> tuple[float, float, int, timedelta, str]:
    """Pure scheduling step → (ease, interval_days, reps, due_in, state)."""
    if rating == "again":
        return _clamp(ease - 0.20), 0.0, 0, RELEARN_STEP, "learning"
    if rating == "hard":
        ease = _clamp(ease - 0.15)
        if reps == 0:
            return ease, 0.0, 0, RELEARN_STEP, "learning"
        interval = max(interval_days * 1.2, 1.0)
        return ease, interval, reps + 1, timedelta(days=interval), "review"
    if rating == "good":
        if reps == 0:
            return ease, 1.0, 1, timedelta(days=1), "learning"
        if reps == 1:
            return ease, 6.0, 2, timedelta(days=6), "review"
        interval = interval_days * ease
        return ease, interval, reps + 1, timedelta(days=interval), "review"
    if rating == "easy":
        ease = _clamp(ease + 0.15)
        if reps == 0:
            return ease, 4.0, 2, timedelta(days=4), "review"
        interval = max(interval_days * ease * 1.3, 4.0)
        return ease, interval, reps + 1, timedelta(days=interval), "review"
    raise ValueError(f"unknown rating: {rating!r}")


def apply_review(word: Word, rating: str) -> None:
    """Advance `word`'s SRS state in place for the given rating."""
    was_review = word.state == "review"
    ease, interval, reps, due_in, state = _schedule(
        word.ease, word.interval_days, word.reps, rating
    )
    if rating == "again" and was_review:
        word.lapses += 1
    word.ease = ease
    word.interval_days = interval
    word.reps = reps
    word.state = state
    word.due_at = utcnow() + due_in
    word.last_review_at = utcnow()


def _humanize(td: timedelta) -> str:
    minutes = td.total_seconds() / 60
    if minutes < 60:
        return f"{round(minutes)}m"
    hours = minutes / 60
    if hours < 24:
        return f"{round(hours)}h"
    return f"{round(td.total_seconds() / 86400)}d"


def next_intervals(word: Word) -> dict[str, str]:
    """Humanized next interval per rating, for the practice-screen buttons."""
    return {
        rating: _humanize(
            _schedule(word.ease, word.interval_days, word.reps, rating)[3]
        )
        for rating in RATINGS
    }


def confidence(word: Word) -> dict:
    """Display confidence derived from the SRS state."""
    if word.state == "new":
        return {"percent": 0, "label": "new"}
    if word.state == "learning":
        return {"percent": 20, "label": "learning"}
    if word.interval_days < 7:
        return {"percent": 45, "label": "familiar"}
    if word.interval_days < 21:
        return {"percent": 75, "label": "confident"}
    return {"percent": 100, "label": "mastered"}
