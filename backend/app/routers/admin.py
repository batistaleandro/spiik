"""Operator administration: list, disable and remove users, and reset
passwords for locked-out learners (no email dependency)."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_admin, hash_password
from app.db import get_db
from app.models import ReviewLog, User, Word
from app.routers.users import purge_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ResetPasswordRequest(BaseModel):
    # omitted/empty → spiik generates a password and returns it once
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return user


@router.get("/users")
def list_users(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Every account with registration date, activity and status."""
    # one grouped query for per-user word counts + last practice time;
    # distinct word ids because the review-log join fans rows out
    stats = {
        row.user_id: (row.word_count, row.last_review_at)
        for row in db.execute(
            select(
                Word.user_id.label("user_id"),
                func.count(func.distinct(Word.id)).label("word_count"),
                func.max(ReviewLog.reviewed_at).label("last_review_at"),
            )
            .outerjoin(ReviewLog, ReviewLog.word_id == Word.id)
            .group_by(Word.user_id)
        )
    }
    users = db.scalars(select(User).order_by(User.created_at, User.id)).all()
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.is_admin,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(timespec="seconds") + "Z",
                "word_count": stats.get(u.id, (0, None))[0],
                "last_review_at": (
                    stats.get(u.id, (0, None))[1].isoformat(timespec="seconds") + "Z"
                    if stats.get(u.id, (0, None))[1]
                    else None
                ),
            }
            for u in users
        ]
    }


@router.post("/users/{user_id}/deactivate")
def toggle_active(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Disable an account (immediate: every protected call 401s) or
    re-enable it — the endpoint toggles."""
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(400, "you cannot disable your own account")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(400, "you cannot remove your own account")
    if user.is_admin:
        raise HTTPException(400, "another admin can only be removed by hand")
    purge_user(db, user)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    req: ResetPasswordRequest | None = None,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Set a new password for a locked-out learner. Without a body a
    one-time password is generated and returned — hand it to the user
    out of band; it is never shown again."""
    user = _get_user_or_404(user_id, db)
    generated = None
    password = req.new_password if req is not None else None
    if not password:
        password = generated = secrets.token_urlsafe(12)
    user.password_hash = hash_password(password)
    db.commit()
    return {"generated_password": generated}
