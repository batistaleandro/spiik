"""v0.5 operator tools & account care: admin panel, password reset,
disable, and account deletion (self-service and admin purge)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import (
    PronunciationSuggestion,
    PronunciationVote,
    ReviewLog,
    User,
    Word,
)


def _register(client, username, email=None):
    res = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email or f"{username}@example.com",
            "password": "s3cretpass",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def _promote_admin(username="ana"):
    from app.db import SessionLocal

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        user.is_admin = True
        db.commit()


def _insert_word(user_id, text="creation"):
    """Saved card + one review, without going through the translate/ML
    pipeline."""
    from app.db import SessionLocal

    with SessionLocal() as db:
        word = Word(
            user_id=user_id,
            text=text,
            approximation="kri-ei-chan",
            expected_ipa="k r i eɪ ʃ ə n",
            native_lang="pt-br",
            target_lang="en-us",
        )
        db.add(word)
        db.flush()
        db.add(
            ReviewLog(
                user_id=user_id,
                word_id=word.id,
                rating="good",
                state="review",
            )
        )
        db.commit()
        return word.id


@pytest.fixture()
def admin(client, auth):
    """'ana' as the operator."""
    _promote_admin()
    return auth


# ---- admin panel -----------------------------------------------------------


def test_admin_endpoints_reject_non_admins(client, auth):
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/users", headers=auth).status_code == 403


def test_admin_lists_users_with_activity(client, admin):
    bob = _register(client, "bob")
    _insert_word(bob["user"]["id"])

    res = client.get("/api/admin/users", headers=admin)
    assert res.status_code == 200
    users = {u["username"]: u for u in res.json()["users"]}
    assert users["bob"]["word_count"] == 1
    assert users["bob"]["last_review_at"] is not None
    assert users["ana"]["word_count"] == 0
    assert users["ana"]["is_admin"] is True
    assert all(u["is_active"] for u in users.values())


def test_disable_blocks_login_and_protected_calls(client, admin):
    bob = _register(client, "bob")
    bob_auth = {"Authorization": f"Bearer {bob['access_token']}"}
    assert client.get("/api/auth/me", headers=bob_auth).status_code == 200

    res = client.post(f"/api/admin/users/{bob['user']['id']}/deactivate", headers=admin)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # live session is cut off immediately and login is refused
    assert client.get("/api/auth/me", headers=bob_auth).status_code == 401
    res = client.post(
        "/api/auth/login", json={"username": "bob", "password": "s3cretpass"}
    )
    assert res.status_code == 403

    # re-enable and everything works again
    res = client.post(f"/api/admin/users/{bob['user']['id']}/deactivate", headers=admin)
    assert res.json()["is_active"] is True
    res = client.post(
        "/api/auth/login", json={"username": "bob", "password": "s3cretpass"}
    )
    assert res.status_code == 200


def test_admin_cannot_disable_self(client, admin):
    res = client.get("/api/auth/me", headers=admin)
    ana_id = res.json()["id"]
    res = client.post(f"/api/admin/users/{ana_id}/deactivate", headers=admin)
    assert res.status_code == 400


# ---- operator password reset ------------------------------------------------


def test_reset_password_generates_one_time_password(client, admin):
    bob = _register(client, "bob")
    res = client.post(
        f"/api/admin/users/{bob['user']['id']}/reset-password", headers=admin
    )
    assert res.status_code == 200
    generated = res.json()["generated_password"]
    assert generated and len(generated) >= 16

    res = client.post(
        "/api/auth/login", json={"username": "bob", "password": "s3cretpass"}
    )
    assert res.status_code == 401
    res = client.post("/api/auth/login", json={"username": "bob", "password": generated})
    assert res.status_code == 200


def test_reset_password_accepts_explicit_password(client, admin):
    bob = _register(client, "bob")
    res = client.post(
        f"/api/admin/users/{bob['user']['id']}/reset-password",
        headers=admin,
        json={"new_password": "new-secretpass"},
    )
    assert res.json()["generated_password"] is None
    res = client.post(
        "/api/auth/login", json={"username": "bob", "password": "new-secretpass"}
    )
    assert res.status_code == 200


# ---- removal (admin purge) --------------------------------------------------


def test_admin_removes_user_and_all_their_data(client, admin):
    bob = _register(client, "bob")
    bob_id = bob["user"]["id"]
    word_id = _insert_word(bob_id)

    res = client.delete(f"/api/admin/users/{bob_id}", headers=admin)
    assert res.status_code == 204
    assert client.post(
        "/api/auth/login", json={"username": "bob", "password": "s3cretpass"}
    ).status_code == 401

    from app.db import SessionLocal

    with SessionLocal() as db:
        assert db.get(Word, word_id) is None
        assert db.scalar(select(ReviewLog).where(ReviewLog.user_id == bob_id)) is None


def test_admin_cannot_remove_self_or_other_admins(client, admin):
    res = client.get("/api/auth/me", headers=admin)
    ana_id = res.json()["id"]
    assert (
        client.delete(f"/api/admin/users/{ana_id}", headers=admin).status_code == 400
    )

    _register(client, "bob")
    _promote_admin("bob")
    res = client.get("/api/admin/users", headers=admin)
    bob_id = next(u["id"] for u in res.json()["users"] if u["username"] == "bob")
    assert client.delete(f"/api/admin/users/{bob_id}", headers=admin).status_code == 400


def test_reset_and_remove_missing_user_404s(client, admin):
    assert (
        client.post("/api/admin/users/9999/reset-password", headers=admin).status_code
        == 404
    )
    assert client.delete("/api/admin/users/9999", headers=admin).status_code == 404


# ---- self-service deletion --------------------------------------------------


def test_delete_me_purges_everything(client, admin):
    """The deleting user's words, reviews, suggestions and votes all go;
    other users' content survives (minus the audience sample)."""
    bob = _register(client, "bob")
    bob_id = bob["user"]["id"]
    bob_auth = {"Authorization": f"Bearer {bob['access_token']}"}
    _insert_word(bob_id)

    # bob suggests a pronunciation; ana votes on it
    res = client.post(
        "/api/pronunciation/suggest",
        headers=bob_auth,
        json={
            "native": "pt-br",
            "target": "en-us",
            "text": "creation",
            "suggested_text": "kri-ei-chan",
        },
    )
    assert res.status_code == 200, res.text
    suggestion_id = next(
        s["id"] for s in res.json()["suggestions"] if s["mine"]
    )
    res = client.post(
        "/api/pronunciation/vote",
        headers=admin,
        json={
            "native": "pt-br",
            "target": "en-us",
            "text": "creation",
            "suggestion_id": suggestion_id,
            "vote": "up",
        },
    )
    assert res.status_code == 200, res.text
    # bob votes on the system pronunciation too
    res = client.post(
        "/api/pronunciation/vote",
        headers=bob_auth,
        json={
            "native": "pt-br",
            "target": "en-us",
            "text": "creation",
            "suggestion_id": None,
            "vote": "down",
        },
    )
    assert res.status_code == 200, res.text

    assert client.delete("/api/users/me", headers=bob_auth).status_code == 204
    assert client.get("/api/auth/me", headers=bob_auth).status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"username": "bob", "password": "s3cretpass"}
        ).status_code
        == 401
    )

    from app.db import SessionLocal
    from app.models import PronunciationSystemVote

    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.username == "bob")) is None
        assert db.scalar(select(Word).where(Word.user_id == bob_id)) is None
        assert db.scalar(select(ReviewLog).where(ReviewLog.user_id == bob_id)) is None
        # the suggestion and every vote on it are gone
        assert (
            db.scalar(
                select(PronunciationVote).where(
                    PronunciationVote.suggestion_id == suggestion_id
                )
            )
            is None
        )
        assert (
            db.scalar(
                select(PronunciationSuggestion).where(
                    PronunciationSuggestion.id == suggestion_id
                )
            )
            is None
        )
        assert (
            db.scalar(
                select(PronunciationSystemVote).where(
                    PronunciationSystemVote.user_id == bob_id
                )
            )
            is None
        )
        # ana is untouched
        assert db.scalar(select(User).where(User.username == "ana")) is not None


def test_delete_me_strips_deleted_user_from_audiences(client):
    """A suggestion kept by its author no longer samples the deleted user
    into its test group."""
    bob = _register(client, "bob")
    ana = _register(client, "carol")  # carol authors the suggestion
    carol_auth = {"Authorization": f"Bearer {ana['access_token']}"}
    res = client.post(
        "/api/pronunciation/suggest",
        headers=carol_auth,
        json={
            "native": "pt-br",
            "target": "en-us",
            "text": "creation",
            "suggested_text": "kri-ei-chan",
        },
    )
    assert res.status_code == 200

    from app.db import SessionLocal

    with SessionLocal() as db:
        suggestion = db.scalar(
            select(PronunciationSuggestion).order_by(PronunciationSuggestion.id)
        )
        assert bob["user"]["id"] in (suggestion.audience or [])
        suggestion_id = suggestion.id

    assert client.delete("/api/users/me", headers={
        "Authorization": f"Bearer {bob['access_token']}"
    }).status_code == 204

    with SessionLocal() as db:
        suggestion = db.get(PronunciationSuggestion, suggestion_id)
        assert suggestion is not None
        assert bob["user"]["id"] not in (suggestion.audience or [])


# ---- first-admin bootstrap --------------------------------------------------


def test_spiik_admin_email_promotes_existing_user(client, monkeypatch):
    _register(client, "bob")
    from app.db import init_db

    monkeypatch.setenv("SPIIK_ADMIN_EMAIL", "bob@example.com")
    init_db()
    from app.db import SessionLocal

    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.username == "bob")).is_admin


def test_spiik_admin_email_ignores_unknown_user(client, monkeypatch):
    from app.db import init_db

    monkeypatch.setenv("SPIIK_ADMIN_EMAIL", "nobody@example.com")
    init_db()  # must not raise
