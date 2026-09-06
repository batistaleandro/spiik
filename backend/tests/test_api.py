"""API-level tests (TestClient, translation mocked — no network)."""

from __future__ import annotations

import app.translate as tr
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _mock_translation(monkeypatch, value: str | None):
    def fake_cached(text, gf, gt, mf, mt, allow_echo=False):
        if value is None:
            return None
        return tr.clean_translation(value, text, allow_echo=allow_echo, first_only=allow_echo)

    monkeypatch.setattr(tr, "_cached", fake_cached)


def test_languages_endpoint_lists_all():
    res = client.get("/api/languages")
    assert res.status_code == 200
    codes = {lang["code"] for lang in res.json()}
    assert {"en-us", "pt-br", "ru"} <= codes


def test_analyze_target_mode(monkeypatch):
    _mock_translation(monkeypatch, "мир")
    res = client.post(
        "/api/analyze",
        json={"native": "ru", "target": "en-us", "text": "world"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "world"
    assert data["query"] == "world"
    assert data["input_lang"] == "target"
    assert data["translated"] == "мир"
    assert data["approximation"]
    assert data["expected_ipa"]


def test_analyze_native_mode_translates_first(monkeypatch):
    # Portuguese speaker types their own word, gets the English word to practice
    _mock_translation(monkeypatch, "creation")
    res = client.post(
        "/api/analyze",
        json={"native": "pt-br", "target": "en-us", "text": "criação", "input_lang": "native"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "creation"
    assert data["query"] == "criação"
    assert data["input_lang"] == "native"
    assert data["translated"] == "criação"  # chip shows the user's own word
    assert data["approximation"] == "cri-ei-chan"


def test_analyze_native_mode_allows_echo(monkeypatch):
    # "hotel" translates to "hotel" — still a valid practice word
    _mock_translation(monkeypatch, "hotel")
    res = client.post(
        "/api/analyze",
        json={"native": "es", "target": "en-us", "text": "hotel", "input_lang": "native"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "hotel"


def test_analyze_native_mode_failure_is_a_clear_error(monkeypatch):
    _mock_translation(monkeypatch, None)
    res = client.post(
        "/api/analyze",
        json={"native": "pt-br", "target": "en-us", "text": "zzzqqq", "input_lang": "native"},
    )
    assert res.status_code == 422
    assert "could not translate" in res.json()["detail"]


def test_analyze_bad_language_404():
    res = client.post(
        "/api/analyze",
        json={"native": "xx", "target": "en-us", "text": "world"},
    )
    assert res.status_code == 404


def test_drill_endpoint():
    res = client.get("/api/drill", params={"sound": "θ", "target": "en-us", "native": "pt-br"})
    assert res.status_code == 200
    data = res.json()
    assert data["description"] == "voiceless dental fricative"
    assert data["examples"]
