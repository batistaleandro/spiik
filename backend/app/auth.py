"""Password hashing (bcrypt) and JWT bearer auth."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import db_file, get_db
from app.models import User

TOKEN_TTL = timedelta(days=30)

_bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    secret = os.environ.get("SPIIK_SECRET")
    if secret:
        return secret
    # no env secret: generate one and persist it next to the DB so that
    # tokens survive restarts of a self-hosted instance
    key_file = db_file().parent / "secret.key"
    try:
        return key_file.read_text().strip()
    except FileNotFoundError:
        key = secrets.token_urlsafe(48)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key)
        key_file.chmod(0o600)
        return key


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid or expired session"
        ) from None
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account no longer exists")
    return user
