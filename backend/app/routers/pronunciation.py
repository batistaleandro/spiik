"""Pronunciation router: thumbs feedback and alternative-prunciation suggestions."""

from __future__ import annotations

import math
import os
import random
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    PronunciationSuggestion,
    PronunciationSystemVote,
    PronunciationVote,
    User,
)
from app.pronunciation import key_for, resolve_pronunciation

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])


class VoteRequest(BaseModel):
    native: str
    target: str
    text: str = Field(min_length=1, max_length=100)
    # null votes on the system-generated pronunciation; an id votes on a
    # specific suggestion
    suggestion_id: int | None = None
    vote: Literal["up", "down"]


class SuggestRequest(BaseModel):
    native: str
    target: str
    text: str = Field(min_length=1, max_length=100)
    suggested_text: str = Field(min_length=1)


def rollout() -> float:
    """Fraction of the userbase sampled into a new suggestion's test group.

    Read at call time so deployments and tests can tune it via
    SPIIK_PRONUNCIATION_ROLLOUT without restarting code changes.
    """
    try:
        value = float(os.getenv("SPIIK_PRONUNCIATION_ROLLOUT", "0.2"))
    except ValueError:
        value = 0.2
    return min(max(value, 0.0), 1.0)


def _sample_audience(db: Session, author_id: int) -> list[int]:
    user_ids = [uid for (uid,) in db.execute(select(User.id)).all() if uid != author_id]
    count = math.ceil(len(user_ids) * rollout())
    return random.sample(user_ids, count) if count else []


@router.get("/feedback")
def pronunciation_feedback(
    native: str,
    target: str,
    text: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return resolve_pronunciation(db, user, native, target, text)


@router.post("/vote")
def vote(
    req: VoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    native, target, folded = key_for(req.native, req.target, req.text)
    if req.suggestion_id is None:
        existing = db.scalar(
            select(PronunciationSystemVote).where(
                PronunciationSystemVote.native_lang == native,
                PronunciationSystemVote.target_lang == target,
                PronunciationSystemVote.word_text == folded,
                PronunciationSystemVote.user_id == user.id,
            )
        )
        if existing:
            existing.vote = req.vote
        else:
            db.add(
                PronunciationSystemVote(
                    native_lang=native,
                    target_lang=target,
                    word_text=folded,
                    user_id=user.id,
                    vote=req.vote,
                )
            )
    else:
        suggestion = db.get(PronunciationSuggestion, req.suggestion_id)
        if suggestion is None or key_for(
            suggestion.native_lang, suggestion.target_lang, suggestion.word_text
        ) != (native, target, folded):
            raise HTTPException(404, "suggestion not found")
        existing = db.scalar(
            select(PronunciationVote).where(
                PronunciationVote.suggestion_id == suggestion.id,
                PronunciationVote.user_id == user.id,
            )
        )
        if existing:
            existing.vote = req.vote
        else:
            db.add(
                PronunciationVote(
                    suggestion_id=suggestion.id,
                    user_id=user.id,
                    vote=req.vote,
                )
            )
    db.commit()
    return resolve_pronunciation(db, user, req.native, req.target, req.text)


@router.post("/suggest")
def suggest(
    req: SuggestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    native, target, folded = key_for(req.native, req.target, req.text)
    # casefold after strip: 'ß' folds to 'ss', so the length bound must be
    # checked on the folded text
    suggested = req.suggested_text.strip().casefold()
    if not suggested or len(suggested) > 255:
        raise HTTPException(422, "pronunciation must be 1–255 characters")

    existing = db.scalar(
        select(PronunciationSuggestion).where(
            PronunciationSuggestion.native_lang == native,
            PronunciationSuggestion.target_lang == target,
            PronunciationSuggestion.word_text == folded,
            PronunciationSuggestion.suggested_text == suggested,
        )
    )
    if existing:
        # the same pronunciation was already suggested — make sure this user
        # can see and vote on it too
        if user.id != existing.author_id and user.id not in (existing.audience or []):
            existing.audience = list(existing.audience or []) + [user.id]
            db.commit()
            db.refresh(existing)
        return resolve_pronunciation(db, user, req.native, req.target, req.text)

    db.add(
        PronunciationSuggestion(
            native_lang=native,
            target_lang=target,
            word_text=folded,
            suggested_text=suggested,
            author_id=user.id,
            audience=_sample_audience(db, user.id),
        )
    )
    db.commit()
    return resolve_pronunciation(db, user, req.native, req.target, req.text)
