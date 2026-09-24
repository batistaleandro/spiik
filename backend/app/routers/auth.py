"""Auth routes: register, login, profile management."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, verify_password
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[\w][\w.\-]*$", re.UNICODE)


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
    return {"id": user.id, "username": user.username, "email": user.email}


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
    db.commit()
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
