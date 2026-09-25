"""Words router: saved-word cards, SRS practice queue, reviews, progress."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import ReviewLog, User, Word, iso, utcnow
from app.pipeline import run_analysis
from app.pronunciation import key_for, resolve_pronunciation, resolve_pronunciation_batch
from app.srs import apply_review, confidence, next_intervals

router = APIRouter(prefix="/api", tags=["words"])

DAILY_NEW_LIMIT = 20  # new cards introduced per day


class SaveWordRequest(BaseModel):
    # always the practice word in the target language — the word shown on
    # the trainer card; the meaning travels separately in `translated`
    text: str = Field(min_length=1, max_length=100)
    native: str
    target: str
    # the translation the client already showed the user; storing it avoids
    # a second provider round-trip that can fail or return garbage
    translated: str | None = Field(default=None, max_length=255)


class ReviewRequest(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]


def card_out(word: Word, pronunciation: dict | None = None) -> dict:
    out = {
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
    if pronunciation is not None:
        out["pronunciation"] = pronunciation
    return out


def cards_out(db: Session, user: User, words: list[Word]) -> list[dict]:
    """Serialize cards with the community-resolved pronunciation on each."""
    resolved = resolve_pronunciation_batch(
        db,
        user,
        [(w.native_lang, w.target_lang, w.text, w.approximation) for w in words],
    )
    return [
        card_out(w, resolved[key_for(w.native_lang, w.target_lang, w.text)])
        for w in words
    ]


@router.post("/words")
def save_word(
    req: SaveWordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    text = req.text.strip()
    if not text:
        raise HTTPException(422, "empty word")
    # case-fold in Python: SQLite's lower() is ASCII-only and would miss
    # duplicates in Cyrillic/Greek/etc.
    pair_words = db.scalars(
        select(Word).where(
            Word.user_id == user.id,
            Word.native_lang == req.native,
            Word.target_lang == req.target,
        )
    ).all()
    folded = text.casefold()
    existing = next((w for w in pair_words if w.text.casefold() == folded), None)
    override = (req.translated or "").strip() or None
    # `text` is the practiced word, in both branches — re-running the
    # native→target translation on it would feed target-language text to
    # the source-language translator and save the garbage it returns
    if existing:
        # re-saving a word updates its content (e.g. a corrected meaning)
        # and keeps the SRS scheduling state
        result = run_analysis(
            req.native,
            req.target,
            text,
            "target",
            translated_override=override if override is not None else existing.translated,
        )
        existing.translated = result["translated"]
        existing.approximation = result["approximation"]
        existing.expected_ipa = " ".join(result["expected_ipa"])
        existing.missing_sounds = result["missing_sounds"]
        db.commit()
        db.refresh(existing)
        return card_out(
            existing,
            resolve_pronunciation(
                db, user, existing.native_lang, existing.target_lang,
                existing.text, existing.approximation,
            ),
        )

    result = run_analysis(
        req.native,
        req.target,
        text,
        "target",
        translated_override=override,
    )
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
    try:
        db.commit()
    except IntegrityError:
        # concurrent save of the same word — the pre-check can't fully
        # close that race
        db.rollback()
        raise HTTPException(409, f"“{text}” is already in your words") from None
    db.refresh(word)
    return JSONResponse(
        status_code=201,
        content=card_out(
            word,
            resolve_pronunciation(
                db, user, word.native_lang, word.target_lang,
                word.text, word.approximation,
            ),
        ),
    )


@router.get("/words")
def list_words(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    words = db.scalars(
        select(Word).where(Word.user_id == user.id).order_by(Word.due_at, Word.id)
    ).all()
    return cards_out(db, user, words)


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
        "items": cards_out(db, user, due + fresh),
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
    return card_out(
        word,
        resolve_pronunciation(
            db, user, word.native_lang, word.target_lang,
            word.text, word.approximation,
        ),
    )


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
