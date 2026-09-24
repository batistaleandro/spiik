"""Words router: saved-word cards, SRS practice queue, reviews, progress."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import ReviewLog, User, Word, iso, utcnow
from app.pipeline import run_analysis
from app.srs import apply_review, confidence, next_intervals

router = APIRouter(prefix="/api", tags=["words"])

DAILY_NEW_LIMIT = 20  # new cards introduced per day


class SaveWordRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100)
    native: str
    target: str
    input_lang: Literal["target", "native"] = "target"


class ReviewRequest(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]


def card_out(word: Word) -> dict:
    return {
        "id": word.id,
        "text": word.text,
        "translated": word.translated,
        "approximation": word.approximation,
        "expected_ipa": word.expected_ipa.split(),
        "native": word.native_lang,
        "target": word.target_lang,
        "missing_sounds": word.missing_sounds or [],
        "created_at": iso(word.created_at),
        "srs": {
            "state": word.state,
            "ease": word.ease,
            "interval_days": word.interval_days,
            "reps": word.reps,
            "lapses": word.lapses,
            "due_at": iso(word.due_at),
            "last_review_at": iso(word.last_review_at),
            "confidence": confidence(word),
            "due": word.due_at <= utcnow(),
            "next_intervals": next_intervals(word),
        },
    }


@router.post("/words", status_code=201)
def save_word(
    req: SaveWordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    text = req.text.strip()
    if not text:
        raise HTTPException(422, "empty word")
    existing = db.scalar(
        select(Word).where(
            Word.user_id == user.id,
            Word.native_lang == req.native,
            Word.target_lang == req.target,
            func.lower(Word.text) == text.lower(),
        )
    )
    if existing:
        raise HTTPException(409, f"“{existing.text}” is already in your words")
    result = run_analysis(req.native, req.target, text, req.input_lang)
    word = Word(
        user_id=user.id,
        text=result["text"],
        translated=result["translated"],
        approximation=result["approximation"],
        expected_ipa=" ".join(result["expected_ipa"]),
        native_lang=result["native"]["code"],
        target_lang=result["target"]["code"],
        missing_sounds=result["missing_sounds"],
        due_at=utcnow(),  # new cards are due immediately
    )
    db.add(word)
    db.commit()
    db.refresh(word)
    return card_out(word)


@router.get("/words")
def list_words(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    words = db.scalars(
        select(Word).where(Word.user_id == user.id).order_by(Word.due_at, Word.id)
    ).all()
    return [card_out(w) for w in words]


@router.delete("/words/{word_id}", status_code=204)
def delete_word(
    word_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    word = db.get(Word, word_id)
    if word is None or word.user_id != user.id:
        raise HTTPException(404, "word not found")
    db.delete(word)
    db.commit()


@router.get("/practice")
def practice_queue(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    due = db.scalars(
        select(Word)
        .where(Word.user_id == user.id, Word.state != "new", Word.due_at <= now)
        .order_by(Word.due_at)
    ).all()

    introduced_today = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.was_new.is_(True),
                ReviewLog.reviewed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
            )
        )
        or 0
    )
    fresh: list[Word] = []
    new_room = DAILY_NEW_LIMIT - introduced_today
    if new_room > 0:
        fresh = list(
            db.scalars(
                select(Word)
                .where(Word.user_id == user.id, Word.state == "new")
                .order_by(Word.created_at)
                .limit(new_room)
            ).all()
        )

    next_due = db.scalar(
        select(func.min(Word.due_at)).where(
            Word.user_id == user.id, Word.state != "new", Word.due_at > now
        )
    )
    return {
        "items": [card_out(w) for w in due + fresh],
        "counts": {"due": len(due), "new": len(fresh)},
        "next_due": iso(next_due),
    }


@router.post("/practice/{word_id}/review")
def review_word(
    word_id: int,
    req: ReviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    word = db.get(Word, word_id)
    if word is None or word.user_id != user.id:
        raise HTTPException(404, "word not found")
    was_new = word.state == "new"
    apply_review(word, req.rating)
    db.add(
        ReviewLog(
            user_id=user.id,
            word_id=word.id,
            rating=req.rating,
            was_new=was_new,
            reviewed_at=utcnow(),
            interval_days=word.interval_days,
            ease=word.ease,
            state=word.state,
        )
    )
    db.commit()
    db.refresh(word)
    return card_out(word)


@router.get("/progress")
def progress(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = (
        db.scalar(select(func.count()).select_from(Word).where(Word.user_id == user.id))
        or 0
    )
    by_state = dict(
        db.execute(
            select(Word.state, func.count())
            .where(Word.user_id == user.id)
            .group_by(Word.state)
        ).all()
    )
    mastered = (
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(
                Word.user_id == user.id,
                Word.state == "review",
                Word.interval_days >= 21,
            )
        )
        or 0
    )
    due_now = (
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(
                Word.user_id == user.id,
                Word.state != "new",
                Word.due_at <= now,
            )
        )
        or 0
    )

    # reviews per day over the last 30 days, zero-filled
    since = today_start - timedelta(days=29)
    day_counts = dict(
        db.execute(
            select(func.date(ReviewLog.reviewed_at), func.count())
            .where(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= since)
            .group_by(func.date(ReviewLog.reviewed_at))
        ).all()
    )
    reviews_30d = [
        {
            "date": (since + timedelta(days=i)).date().isoformat(),
            "count": day_counts.get((since + timedelta(days=i)).date().isoformat(), 0),
        }
        for i in range(30)
    ]

    # practice streak: consecutive days with at least one review, ending
    # today (or yesterday, if today's session hasn't happened yet)
    review_dates = {
        str(d)
        for d in db.execute(
            select(func.date(ReviewLog.reviewed_at))
            .where(ReviewLog.user_id == user.id)
            .distinct()
        ).scalars()
    }
    streak = 0
    day = now.date()
    if day.isoformat() not in review_dates:
        day -= timedelta(days=1)
    while day.isoformat() in review_dates:
        streak += 1
        day -= timedelta(days=1)

    # due forecast for the next 7 days (day 0 includes everything overdue)
    forecast = []
    for i in range(7):
        start = today_start + timedelta(days=i)
        end = start + timedelta(days=1)
        condition = Word.due_at <= end if i == 0 else (Word.due_at > start) & (Word.due_at <= end)
        n = (
            db.scalar(
                select(func.count())
                .select_from(Word)
                .where(Word.user_id == user.id, Word.state != "new", condition)
            )
            or 0
        )
        forecast.append({"date": start.date().isoformat(), "count": n})

    return {
        "total": total,
        "new": by_state.get("new", 0),
        "learning": by_state.get("learning", 0),
        "review": by_state.get("review", 0),
        "mastered": mastered,
        "due_now": due_now,
        "streak": streak,
        "reviews_last_30d": reviews_30d,
        "forecast": forecast,
    }
