"""Auth routes: register, login, profile management, password recovery."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, verify_password
from app.db import get_db
from app.email import send_password_reset_email
from app.models import PasswordResetToken, User, utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[\w][\w.\-]*$", re.UNICODE)

RESET_TOKEN_TTL = timedelta(hours=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
    }


def _check_username(username: str, db: Session, *, exclude_id: int | None = None) -> str:
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise HTTPException(
            422,
            "username may contain letters, numbers, dots, dashes and underscores "
            "and must start with a letter or number",
        )
    taken = db.scalar(
        select(func.count())
        .select_from(User)
        .where(func.lower(User.username) == username.lower(), User.id != exclude_id)
    )
    if taken:
        raise HTTPException(409, "username already taken")
    return username


def _check_email(email: str, db: Session, *, exclude_id: int | None = None) -> str:
    email = email.strip().lower()
    taken = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.email == email, User.id != exclude_id)
    )
    if taken:
        raise HTTPException(409, "email already registered")
    return email


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    username = _check_username(req.username, db)
    email = _check_email(str(req.email), db)
    user = User(username=username, email=email, password_hash=hash_password(req.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # the lower() pre-check is ASCII-only, so case-variants of
        # non-Latin usernames land here — still a clean 409
        db.rollback()
        raise HTTPException(409, "username or email already registered") from None
    db.refresh(user)
    return {"access_token": create_token(user), "token_type": "bearer", "user": user_out(user)}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict:
    ident = req.username.strip()
    user = db.scalar(select(User).where(func.lower(User.username) == ident.lower()))
    if user is None:
        user = db.scalar(select(User).where(User.email == ident.lower()))
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "wrong username or password")
    if not user.is_active:
        raise HTTPException(403, "account disabled — ask the operator to re-enable it")
    return {"access_token": create_token(user), "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_out(user)


@router.patch("/me")
def update_me(
    req: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if req.username is not None:
        user.username = _check_username(req.username, db, exclude_id=user.id)
    if req.email is not None:
        user.email = _check_email(str(req.email), db, exclude_id=user.id)
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    req: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(403, "current password is wrong")
    user.password_hash = hash_password(req.new_password)
    db.commit()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    """Mail a one-time reset link. Always 204 — answering differently for
    unknown addresses would reveal who has an account."""
    email = str(req.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        return
    token = secrets.token_urlsafe(32)
    # a fresh request supersedes links that are still outstanding
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=utcnow() + RESET_TOKEN_TTL,
        )
    )
    db.commit()
    # SMTP misconfiguration is logged by the sender, never surfaced here
    send_password_reset_email(user.email, token)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(req: PasswordReset, db: Session = Depends(get_db)) -> None:
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_token(req.token)
        )
    )
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise HTTPException(400, "invalid or expired reset link")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(400, "invalid or expired reset link")
    user.password_hash = hash_password(req.new_password)
    row.used_at = utcnow()
    db.commit()
