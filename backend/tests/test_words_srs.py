"""Saved words + SRS scheduling tests (translation mocked — no network)."""

from __future__ import annotations

import app.translate as tr


def _mock_translation(monkeypatch, value: str | None):
    def fake_cached(text, gf, gt, mf, mt, allow_echo=False):
        if value is None:
            return None
        return tr.clean_translation(value, text, allow_echo=allow_echo, first_only=allow_echo)

    monkeypatch.setattr(tr, "_cached", fake_cached)


def _save(client, auth, text="world", **overrides):
    body = {"text": text, "native": "pt-br", "target": "en-us", **overrides}
    return client.post("/api/words", headers=auth, json=body)


def test_save_word_runs_analysis_server_side(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    res = _save(client, auth)
    assert res.status_code == 201, res.text
    card = res.json()
    assert card["text"] == "world"
    assert card["translated"] == "mundo"
    assert card["approximation"]
    assert card["expected_ipa"]
    assert card["native"] == "pt-br"
    assert card["target"] == "en-us"
    assert card["srs"]["state"] == "new"
    assert card["srs"]["confidence"] == {"percent": 0, "label": "new"}
    assert card["srs"]["due"] is True


def test_native_mode_save_honors_client_translation(client, auth, monkeypatch):
    # the meaning the client showed the user must survive a native-mode
    # save — not be replaced by the practice word
    _mock_translation(monkeypatch, "привет")
    res = client.post(
        "/api/words",
        headers=auth,
        json={
            "text": "Привет",
            "native": "pt-br",
            "target": "ru",
            "input_lang": "native",
            "translated": "oi",
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["translated"] == "oi"


def test_save_keeps_practice_word_no_retranslation(client, auth, monkeypatch):
    # the trainer card shows "oi" translated to "Привет"; saving sends that
    # practice word. Re-running the pt→ru translation on it (as the save
    # endpoint used to) feeds Russian text to the pt→en Marian model, which
    # answers with garbage — surfaced in Russian as "Не знаю" — and that
    # garbage became the saved word. The text is already the practice word;
    # it must never be translated again. `input_lang` is sent here the way
    # currently-deployed frontends still do and must be ignored.
    def fake_cached(text, gf, gt, mf, mt, allow_echo=False):
        if (gf, gt) == ("pt", "ru"):
            # what the local pt→en+en→ru pivot really returns for "Привет"
            return tr.clean_translation("Не знаю", text, allow_echo=allow_echo)
        return tr.clean_translation("oi", text, allow_echo=allow_echo)

    monkeypatch.setattr(tr, "_cached", fake_cached)
    res = client.post(
        "/api/words",
        headers=auth,
        json={
            "text": "Привет",
            "native": "pt-br",
            "target": "ru",
            "input_lang": "native",
            "translated": "oi",
        },
    )
    assert res.status_code == 201, res.text
    card = res.json()
    assert card["text"] == "Привет"
    assert card["translated"] == "oi"
    assert card["approximation"]
    assert card["expected_ipa"]


def test_duplicate_save_updates_meaning(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    assert _save(client, auth).status_code == 201
    # re-saving the same word (any case) updates its meaning and keeps
    # one single card
    res = _save(client, auth, text="WORLD")
    assert res.status_code == 200, res.text
    card = res.json()
    assert card["text"] == "world"
    assert card["srs"]["state"] == "new"
    assert len(client.get("/api/words", headers=auth).json()) == 1


def test_duplicate_cyrillic_word_upserts_without_500(client, auth, monkeypatch):
    # SQLite's lower() is ASCII-only — the duplicate check must case-fold
    # in Python or a repeated Cyrillic save crashes with a raw 500
    _mock_translation(monkeypatch, "привет")
    first = _save(client, auth, text="привет", target="ru")
    assert first.status_code == 201, first.text
    second = _save(client, auth, text="ПРИВЕТ", target="ru", translated="oi")
    assert second.status_code == 200, second.text
    assert second.json()["translated"] == "oi"
    words = client.get("/api/words", headers=auth).json()
    assert len(words) == 1
    assert words[0]["translated"] == "oi"


def test_save_word_stores_client_translation(client, auth, monkeypatch):
    # the translation the user already saw wins over a fresh provider
    # round-trip (which can fail or return garbage at save time)
    monkeypatch.setattr(tr, "_cached", lambda *a, **k: "GARBAGE")
    res = client.post(
        "/api/words",
        headers=auth,
        json={
            "text": "world",
            "native": "pt-br",
            "target": "en-us",
            "translated": "mundo",
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["translated"] == "mundo"


def test_list_words(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    _save(client, auth, text="world")
    _save(client, auth, text="think")
    res = client.get("/api/words", headers=auth)
    assert res.status_code == 200
    assert [w["text"] for w in res.json()] == ["world", "think"]


def test_review_good_graduates_to_review(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    card = _save(client, auth).json()

    first = client.post(
        f"/api/practice/{card['id']}/review", headers=auth, json={"rating": "good"}
    ).json()
    assert first["srs"]["state"] == "learning"
    assert first["srs"]["reps"] == 1
    assert first["srs"]["interval_days"] == 1

    second = client.post(
        f"/api/practice/{card['id']}/review", headers=auth, json={"rating": "good"}
    ).json()
    assert second["srs"]["state"] == "review"
    assert second["srs"]["interval_days"] == 6

    third = client.post(
        f"/api/practice/{card['id']}/review", headers=auth, json={"rating": "good"}
    ).json()
    assert third["srs"]["interval_days"] == 6 * second["srs"]["ease"]
    assert third["srs"]["confidence"]["label"] == "confident"


def test_review_again_reschedules_soon_and_counts_lapse(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    card = _save(client, auth).json()
    for rating in ("good", "good"):
        client.post(f"/api/practice/{card['id']}/review", headers=auth, json={"rating": rating})

    again = client.post(
        f"/api/practice/{card['id']}/review", headers=auth, json={"rating": "again"}
    ).json()
    assert again["srs"]["state"] == "learning"
    assert again["srs"]["reps"] == 0
    assert again["srs"]["lapses"] == 1
    assert again["srs"]["ease"] == 2.5 - 0.20


def test_practice_queue_dries_up_then_returns(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    card = _save(client, auth).json()

    queue = client.get("/api/practice", headers=auth).json()
    assert [w["id"] for w in queue["items"]] == [card["id"]]
    assert queue["counts"] == {"due": 0, "new": 1}

    client.post(f"/api/practice/{card['id']}/review", headers=auth, json={"rating": "good"})

    queue = client.get("/api/practice", headers=auth).json()
    assert queue["items"] == []
    assert queue["next_due"] is not None


def test_progress_aggregates(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    _save(client, auth, text="world")
    _save(client, auth, text="think")

    first = client.get("/api/words", headers=auth).json()[0]
    client.post(f"/api/practice/{first['id']}/review", headers=auth, json={"rating": "good"})

    res = client.get("/api/progress", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["new"] == 1
    assert data["learning"] == 1
    assert data["due_now"] == 0
    assert data["streak"] == 1
    assert sum(d["count"] for d in data["reviews_last_30d"]) == 1
    assert data["reviews_last_30d"][-1]["count"] == 1
    assert len(data["forecast"]) == 7


def test_delete_word(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    card = _save(client, auth).json()

    other = client.post(
        "/api/auth/register",
        json={"username": "beto", "email": "beto@example.com", "password": "longenough1"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    # another user can't delete it, and can't see it in their queue
    assert (
        client.delete(f"/api/words/{card['id']}", headers=other_headers).status_code == 404
    )
    assert client.delete(f"/api/words/{card['id']}", headers=auth).status_code == 204
    assert client.get("/api/words", headers=auth).json() == []
