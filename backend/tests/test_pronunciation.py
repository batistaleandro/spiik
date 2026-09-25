"""Community pronunciation suggestions + voting tests (translation mocked — no network)."""

from __future__ import annotations

import app.routers.pronunciation as pron
import app.translate as tr


def _mock_translation(monkeypatch, value: str | None):
    def fake_cached(text, gf, gt, mf, mt, allow_echo=False):
        if value is None:
            return None
        return tr.clean_translation(value, text, allow_echo=allow_echo, first_only=allow_echo)

    monkeypatch.setattr(tr, "_cached", fake_cached)


def _register(client, username: str, email: str):
    res = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "s3cretpass"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _save(client, auth, text: str = "world"):
    return client.post(
        "/api/words", headers=auth, json={"text": text, "native": "pt-br", "target": "en-us"}
    )


def _feedback(client, auth, text: str = "world"):
    return client.get(
        "/api/pronunciation/feedback",
        headers=auth,
        params={"native": "pt-br", "target": "en-us", "text": text},
    )


def _suggest(client, auth, text: str = "world", suggested: str = "uer-oeld"):
    return client.post(
        "/api/pronunciation/suggest",
        headers=auth,
        json={"native": "pt-br", "target": "en-us", "text": text, "suggested_text": suggested},
    )


def _vote(client, auth, suggestion_id: int | None, vote: str, text: str = "world"):
    return client.post(
        "/api/pronunciation/vote",
        headers=auth,
        json={
            "native": "pt-br",
            "target": "en-us",
            "text": text,
            "suggestion_id": suggestion_id,
            "vote": vote,
        },
    )


def test_rollout_env_config(monkeypatch):
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0.35")
    assert pron.rollout() == 0.35
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "1.5")
    assert pron.rollout() == 1.0
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "-2")
    assert pron.rollout() == 0.0
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "nonsense")
    assert pron.rollout() == 0.2
    monkeypatch.delenv("SPIIK_PRONUNCIATION_ROLLOUT")
    assert pron.rollout() == 0.2


def test_vote_on_system_pronunciation_upserts(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    res = _vote(client, auth, None, "up")
    assert res.status_code == 200, res.text
    fb = res.json()
    assert fb["system"] == {"up": 1, "down": 0, "my_vote": "up"}
    # changing the vote replaces it instead of adding a second one
    res = _vote(client, auth, None, "down")
    fb = res.json()
    assert fb["system"] == {"up": 0, "down": 1, "my_vote": "down"}
    assert fb["effective"]["source"] == "system"
    assert fb["suggestions"] == []


def test_suggest_author_sees_own_suggestion(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")  # nobody else sees it
    res = _save(client, auth)
    approx = res.json()["approximation"]
    res = _suggest(client, auth, suggested="uer-oeld")
    assert res.status_code == 200, res.text
    fb = res.json()
    assert len(fb["suggestions"]) == 1
    s = fb["suggestions"][0]
    assert s["text"] == "uer-oeld"
    assert s["mine"] is True
    assert s["up"] == 0 and s["down"] == 0
    assert s["promoted"] is False
    # the author sees their own suggestion even with no votes
    assert fb["effective"] == {"source": "suggestion", "text": "uer-oeld", "suggestion_id": s["id"]}
    # the saved card keeps the system approximation as its snapshot but
    # surfaces the suggestion as the effective pronunciation
    card = _save(client, auth).json()
    assert card["approximation"] == approx
    assert card["pronunciation"]["effective"]["text"] == "uer-oeld"


def test_suggest_matches_word_key_case_insensitively(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, text="world")
    res = _feedback(client, auth, text="WORLD")
    assert res.status_code == 200, res.text
    assert len(res.json()["suggestions"]) == 1


def test_suggest_samples_audience_from_userbase(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    carla = _register(client, "carla", "carla@example.com")
    # rollout 1.0: every non-author user is sampled into the audience
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "1.0")
    _suggest(client, auth)
    for headers in (bruno, carla):
        fb = _feedback(client, headers).json()
        assert fb["effective"]["source"] == "suggestion"
        assert fb["suggestions"][0]["in_audience"] is True

    # a fresh suggestion with rollout 0 reaches nobody
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="voeld")
    fb = _feedback(client, carla).json()
    assert len(fb["suggestions"]) == 2
    targeted = [s for s in fb["suggestions"] if s["text"] == "voeld"]
    assert targeted and targeted[0]["in_audience"] is False
    # she still sees the suggestion she was sampled into
    assert fb["effective"]["text"] == "uer-oeld"


def test_duplicate_suggest_returns_existing_and_adds_audience(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="uer-oeld")
    # bruno suggests the very same text — no duplicate is created, but he
    # becomes able to see and vote on it
    res = _suggest(client, bruno, suggested="uer-oeld")
    assert res.status_code == 200, res.text
    fb = res.json()
    assert len(fb["suggestions"]) == 1
    assert fb["suggestions"][0]["mine"] is False
    assert fb["suggestions"][0]["in_audience"] is True
    assert fb["effective"]["text"] == "uer-oeld"


def test_promotion_when_rate_surpasses_system(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    carla = _register(client, "carla", "carla@example.com")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="uer-oeld")
    fb = _feedback(client, auth).json()
    suggestion_id = fb["suggestions"][0]["id"]

    # an unvoted system pronunciation sits at a neutral 0.5; the suggestion
    # with no votes (rate 0) must not replace it
    for headers in (bruno, carla):
        assert _feedback(client, headers).json()["effective"]["source"] == "system"

    # one upvote puts the suggestion at 1.0 > 0.5 — it becomes the default
    # for everyone, including users outside the audience
    res = _vote(client, bruno, suggestion_id, "up")
    assert res.status_code == 200, res.text
    for headers in (bruno, carla):
        fb = _feedback(client, headers).json()
        assert fb["effective"]["source"] == "suggestion"
        assert fb["suggestions"][0]["promoted"] is True


def test_promotion_requires_strictly_surpassing_system_rate(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    carla = _register(client, "carla", "carla@example.com")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="uer-oeld")
    fb = _feedback(client, auth).json()
    suggestion_id = fb["suggestions"][0]["id"]

    # system upvoted once (rate 1.0); the suggestion with one upvote (1.0)
    # ties and must NOT replace the system default
    _vote(client, carla, None, "up")
    _vote(client, bruno, suggestion_id, "up")
    for headers in (bruno, carla):
        assert _feedback(client, headers).json()["effective"]["source"] == "system"

    # the system dropping to 0.5 lets the 1.0 suggestion take over
    _vote(client, carla, None, "down")
    fb = _feedback(client, carla).json()
    assert fb["effective"]["source"] == "suggestion"
    assert fb["system"] == {"up": 0, "down": 1, "my_vote": "down"}


def test_no_promotion_when_suggestion_disliked(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="uer-oeld")
    fb = _feedback(client, auth).json()
    suggestion_id = fb["suggestions"][0]["id"]
    _vote(client, bruno, suggestion_id, "down")
    # bruno (not author, not in the audience) falls back to the system one;
    # the author still sees her own suggestion
    fb = _feedback(client, bruno).json()
    assert fb["effective"]["source"] == "system"
    fb = _feedback(client, auth).json()
    assert fb["effective"]["source"] == "suggestion"
    assert fb["suggestions"][0]["promoted"] is False
    assert fb["suggestions"][0]["down"] == 1


def test_highest_rate_wins_among_multiple_suggestions(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    bruno = _register(client, "bruno", "bruno@example.com")
    carla = _register(client, "carla", "carla@example.com")
    dana = _register(client, "dana", "dana@example.com")
    monkeypatch.setenv("SPIIK_PRONUNCIATION_ROLLOUT", "0")
    _suggest(client, auth, suggested="uer-oeld")
    _suggest(client, bruno, suggested="uorld")
    fb = _feedback(client, auth).json()
    by_text = {s["text"]: s["id"] for s in fb["suggestions"]}
    assert set(by_text) == {"uer-oeld", "uorld"}

    # one vote each — tied on rate; then a second vote for "uorld" gives it
    # the same rate but more votes, so it wins
    _vote(client, carla, by_text["uer-oeld"], "up")
    _vote(client, carla, by_text["uorld"], "up")
    _vote(client, dana, by_text["uorld"], "up")
    fb = _feedback(client, dana).json()
    assert fb["effective"]["source"] == "suggestion"
    assert fb["effective"]["text"] == "uorld"
    promoted = [s for s in fb["suggestions"] if s["promoted"]]
    assert len(promoted) == 1 and promoted[0]["text"] == "uorld"


def test_card_payloads_include_pronunciation(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    card = _save(client, auth).json()
    p = card["pronunciation"]
    assert p["system"] == {"up": 0, "down": 0, "my_vote": None}
    assert p["suggestions"] == []
    assert p["effective"] == {
        "source": "system",
        "text": card["approximation"],
        "suggestion_id": None,
    }
    assert p["native"] == "pt-br" and p["target"] == "en-us"
    # the practice queue surfaces the same payload
    queue = client.get("/api/practice", headers=auth).json()
    assert queue["items"][0]["pronunciation"]["effective"]["source"] == "system"


def test_vote_unknown_suggestion_returns_404(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    res = _vote(client, auth, 999, "up")
    assert res.status_code == 404, res.text


def test_suggest_empty_or_overlong_returns_422(client, auth, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    assert _suggest(client, auth, suggested="   ").status_code == 422
    assert _suggest(client, auth, suggested="x" * 256).status_code == 422
    # 255 characters is accepted
    assert _suggest(client, auth, suggested="x" * 255).status_code == 200


def test_feedback_requires_auth(client, monkeypatch):
    _mock_translation(monkeypatch, "mundo")
    res = client.get(
        "/api/pronunciation/feedback",
        params={"native": "pt-br", "target": "en-us", "text": "world"},
    )
    assert res.status_code == 401, res.text
