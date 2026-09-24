"""Auth endpoint tests: register, login, profile management."""

from __future__ import annotations


def test_register_and_me(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "leo", "email": "leo@example.com", "password": "longenough1"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["user"]["username"] == "leo"
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {"id": body["user"]["id"], "username": "leo", "email": "leo@example.com"}


def test_register_rejects_short_password(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "leo", "email": "leo@example.com", "password": "short"},
    )
    assert res.status_code == 422


def test_register_rejects_bad_email(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "leo", "email": "not-an-email", "password": "longenough1"},
    )
    assert res.status_code == 422


def test_register_duplicate_username_case_insensitive(client):
    for username in ("ana", "ANA"):
        res = client.post(
            "/api/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": "longenough1"},
        )
    assert res.status_code == 409
    assert "username" in res.json()["detail"]


def test_register_duplicate_email(client, auth):
    res = client.post(
        "/api/auth/register",
        json={"username": "other", "email": "ana@example.com", "password": "longenough1"},
    )
    assert res.status_code == 409


def test_login_with_username_and_with_email(client, auth):
    by_name = client.post(
        "/api/auth/login", json={"username": "ana", "password": "s3cretpass"}
    )
    assert by_name.status_code == 200
    by_email = client.post(
        "/api/auth/login", json={"username": "ana@example.com", "password": "s3cretpass"}
    )
    assert by_email.status_code == 200
    assert by_email.json()["access_token"]


def test_login_wrong_password(client, auth):
    res = client.post("/api/auth/login", json={"username": "ana", "password": "wrongpass99"})
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    ).status_code == 401


def test_update_profile(client, auth):
    res = client.patch("/api/auth/me", headers=auth, json={"email": "new@example.com"})
    assert res.status_code == 200
    assert res.json()["email"] == "new@example.com"

    res = client.patch("/api/auth/me", headers=auth, json={"username": "anita"})
    assert res.status_code == 200
    assert res.json()["username"] == "anita"

    # old username can be reused by someone else now
    res = client.post(
        "/api/auth/register",
        json={"username": "ana", "email": "reuse@example.com", "password": "longenough1"},
    )
    assert res.status_code == 201


def test_update_profile_conflicts(client, auth):
    client.post(
        "/api/auth/register",
        json={"username": "beto", "email": "beto@example.com", "password": "longenough1"},
    )
    assert (
        client.patch("/api/auth/me", headers=auth, json={"username": "beto"}).status_code == 409
    )
    assert (
        client.patch(
            "/api/auth/me", headers=auth, json={"email": "beto@example.com"}
        ).status_code
        == 409
    )


def test_change_password(client, auth):
    res = client.put(
        "/api/auth/password",
        headers=auth,
        json={"current_password": "s3cretpass", "new_password": "brandnewpass1"},
    )
    assert res.status_code == 204

    assert (
        client.post(
            "/api/auth/login", json={"username": "ana", "password": "s3cretpass"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"username": "ana", "password": "brandnewpass1"}
        ).status_code
        == 200
    )


def test_change_password_wrong_current(client, auth):
    res = client.put(
        "/api/auth/password",
        headers=auth,
        json={"current_password": "nope-nope", "new_password": "brandnewpass1"},
    )
    assert res.status_code == 403


def test_saved_words_require_auth(client):
    res = client.get("/api/words")
    assert res.status_code == 401
