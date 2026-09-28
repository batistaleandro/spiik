"""Email password recovery: forgot-password → emailed one-time link → reset."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import PasswordResetToken, utcnow


@pytest.fixture()
def sent_links(monkeypatch):
    """Capture the tokens the backend would email, without SMTP."""
    import app.routers.auth as auth_router

    tokens: list[tuple[str, str]] = []  # (email, token)
    monkeypatch.setattr(
        auth_router,
        "send_password_reset_email",
        lambda to, token: tokens.append((to, token)),
    )
    return tokens


def _register(client, username="leo", email="leo@example.com"):
    res = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "longenough1"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_forgot_password_never_reveals_accounts(client, sent_links):
    res = client.post(
        "/api/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert res.status_code == 204
    assert sent_links == []


def test_full_reset_flow(client, sent_links):
    _register(client)
    res = client.post(
        "/api/auth/forgot-password", json={"email": "leo@example.com"}
    )
    assert res.status_code == 204
    assert len(sent_links) == 1
    to, token = sent_links[0]
    assert to == "leo@example.com"

    res = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "brand-new-pass"},
    )
    assert res.status_code == 204

    assert (
        client.post(
            "/api/auth/login",
            json={"username": "leo", "password": "brand-new-pass"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "leo", "password": "longenough1"},
        ).status_code
        == 401
    )


def test_reset_token_is_single_use(client, sent_links):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "leo@example.com"})
    _, token = sent_links[0]

    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "brand-new-pass"},
        ).status_code
        == 204
    )
    # replaying the same link must fail
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "another-pass1"},
        ).status_code
        == 400
    )


def test_new_request_invalidates_outstanding_links(client, sent_links):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "leo@example.com"})
    client.post("/api/auth/forgot-password", json={"email": "leo@example.com"})
    assert len(sent_links) == 2

    # the first link no longer works, the second does
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": sent_links[0][1], "new_password": "brand-new-pass"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": sent_links[1][1], "new_password": "brand-new-pass"},
        ).status_code
        == 204
    )


def test_reset_rejects_expired_token(client, sent_links):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "leo@example.com"})
    _, token = sent_links[0]

    from app.db import SessionLocal

    with SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken))
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "brand-new-pass"},
        ).status_code
        == 400
    )


def test_reset_rejects_unknown_token(client):
    res = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "brand-new-pass"},
    )
    assert res.status_code == 400
