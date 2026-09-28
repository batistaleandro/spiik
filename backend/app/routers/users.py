"""Self-service account care: `DELETE /api/users/me` and the shared
user-data purge used by the admin router as well."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
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

router = APIRouter(prefix="/api/users", tags=["users"])


def purge_user(db: Session, user: User) -> None:
    """Delete a user and every trace of them.

    Words and review logs go through the ORM cascades; the pronunciation
    community tables carry raw user ids with no FK cascade, so they are
    cleaned up explicitly here.
    """
    uid = user.id
    my_suggestions = select(PronunciationSuggestion.id).where(
        PronunciationSuggestion.author_id == uid
    )
    db.query(PronunciationVote).filter(
        (PronunciationVote.user_id == uid)
        | PronunciationVote.suggestion_id.in_(my_suggestions)
    ).delete(synchronize_session=False)
    db.query(PronunciationSystemVote).filter(
        PronunciationSystemVote.user_id == uid
    ).delete(synchronize_session=False)
    db.query(PronunciationSuggestion).filter(
        PronunciationSuggestion.author_id == uid
    ).delete(synchronize_session=False)
    # the user may still be sampled into the audience of other people's
    # suggestions — audience is a JSON list of raw user ids
    for suggestion in db.scalars(select(PronunciationSuggestion)):
        if suggestion.audience and uid in suggestion.audience:
            suggestion.audience = [a for a in suggestion.audience if a != uid]
    db.delete(user)
    db.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the account: profile, saved words and review
    history. There is no undo."""
    purge_user(db, user)
