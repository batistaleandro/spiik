"""Translation chain tests: parsers, pair plans, provider ordering."""

from __future__ import annotations

import app.translate as tr
from app import translate_local


# ---- gtx JSON parser --------------------------------------------------------


def test_parse_gtx_joins_sentence_segments():
    data = {
        "sentences": [
            {"trans": "Como ", "orig": "How are"},
            {"trans": "você?", "orig": " you?"},
        ]
    }
    assert tr._parse_gtx(data) == "Como você?"


def test_parse_gtx_handles_garbage():
    assert tr._parse_gtx({}) is None
    assert tr._parse_gtx({"sentences": []}) is None
    assert tr._parse_gtx(["not", "a", "dict"]) is None
    assert tr._parse_gtx({"sentences": [{"orig": "no trans field"}]}) is None


# ---- dict-chrome-ex JSON parser ------------------------------------------------


def test_parse_chrome_joins_plain_segments():
    assert tr._parse_chrome(["บ้าน"]) == "บ้าน"
    assert tr._parse_chrome(["สวัสดี", " ครับ"]) == "สวัสดี ครับ"


def test_parse_chrome_takes_first_cell_of_rows():
    assert tr._parse_chrome([["บ้าน", "house"], ["ที", "team"]]) == "บ้านที"


def test_parse_chrome_handles_garbage():
    assert tr._parse_chrome(None) is None
    assert tr._parse_chrome({}) is None
    assert tr._parse_chrome([]) is None
    assert tr._parse_chrome([[None, "house"]]) is None


def test_google_falls_back_to_chrome_endpoint(monkeypatch):
    # gtx rate-limits hard by IP (429); the Chrome endpoint has a
    # separate quota and must take over
    class RateLimited:
        def raise_for_status(self):
            import requests

            raise requests.HTTPError("429")

        def json(self):
            return {}

    def chrome_ok(url, **kwargs):
        class Ok:
            def raise_for_status(self):
                return None

            def json(self):
                return ["บ้าน"]

        assert "clients5.google.com" in url
        assert kwargs["params"]["tl"] == "th"
        return Ok()

    monkeypatch.setattr(
        tr.requests,
        "get",
        lambda url, **kw: (
            RateLimited() if "translate.googleapis.com" in url else chrome_ok(url, **kw)
        ),
    )
    assert tr._google("house", "en", "th") == "บ้าน"


def test_google_prefers_gtx_when_it_works(monkeypatch):
    def ok(url, **kwargs):
        class Ok:
            def raise_for_status(self):
                return None

            def json(self):
                if "translate.googleapis.com" in url:
                    return {"sentences": [{"trans": "บ้าน"}]}
                raise AssertionError("chrome endpoint should not be called")

        return Ok()

    monkeypatch.setattr(tr.requests, "get", ok)
    assert tr._google("house", "en", "th") == "บ้าน"


# ---- Marian pair plans --------------------------------------------------------


def test_direct_pair_is_one_hop():
    plan = translate_local.pair_plan("en", "pt")
    assert plan == [("Helsinki-NLP/opus-mt-tc-big-en-pt", None, "pob")]


def test_brazilian_portuguese_uses_pob_token():
    _, _, dst_token = translate_local.pair_plan("en", "pt")[0]
    assert dst_token == "pob"


def test_same_language_needs_no_model():
    assert translate_local.pair_plan("en", "en") == []


def test_unsupported_pair_pivots_through_english():
    plan = translate_local.pair_plan("pt", "de")
    assert plan == [
        ("Helsinki-NLP/opus-mt-ROMANCE-en", None, None),
        ("Helsinki-NLP/opus-mt-en-de", None, None),
    ]


def test_unsupported_pair_without_pivot_is_empty():
    assert translate_local.pair_plan("de", "ja") == []


def test_thai_to_english_is_a_direct_pair():
    assert translate_local.pair_plan("th", "en") == [
        ("Helsinki-NLP/opus-mt-th-en", None, None)
    ]


def test_thai_to_other_languages_pivot_through_english():
    plan = translate_local.pair_plan("th", "de")
    assert plan == [
        ("Helsinki-NLP/opus-mt-th-en", None, None),
        ("Helsinki-NLP/opus-mt-en-de", None, None),
    ]
    # no en→th Marian model exists: the hosted chain covers that direction
    assert translate_local.pair_plan("en", "th") == []
    assert translate_local.pair_plan("pt", "th") == []


# ---- provider chain ordering ---------------------------------------------------


def test_chain_tries_local_first_when_available(monkeypatch):
    monkeypatch.setenv("SPIIK_TRANSLATE", "auto")
    monkeypatch.setattr(translate_local, "available", lambda: True)
    calls: list[str] = []

    def fake(name, text, src, dst, allow_echo=False):
        calls.append(name)
        return None

    monkeypatch.setattr(tr, "_run_provider", fake)
    tr._cached.cache_clear()
    tr._cached("world", "en", "pt", "en-US", "pt-BR")
    tr._cached.cache_clear()
    assert calls == ["local", "google", "mymemory"]


def test_chain_skips_local_in_online_mode(monkeypatch):
    monkeypatch.setenv("SPIIK_TRANSLATE", "online")
    calls: list[str] = []

    def fake(name, text, src, dst, allow_echo=False):
        calls.append(name)
        return None

    monkeypatch.setattr(tr, "_run_provider", fake)
    tr._cached.cache_clear()
    tr._cached("world", "en", "pt", "en-US", "pt-BR")
    tr._cached.cache_clear()
    assert calls == ["google", "mymemory"]


def test_chain_off_disables_translation(monkeypatch):
    monkeypatch.setenv("SPIIK_TRANSLATE", "off")
    called = []

    def fake(name, text, src, dst, allow_echo=False):
        called.append(name)
        return "x"

    monkeypatch.setattr(tr, "_run_provider", fake)
    tr._cached.cache_clear()
    assert tr._cached("world", "en", "pt", "en-US", "pt-BR") is None
    tr._cached.cache_clear()
    assert called == []


def test_chain_returns_first_success(monkeypatch):
    monkeypatch.setenv("SPIIK_TRANSLATE", "online")

    def fake(name, text, src, dst, allow_echo=False):
        return None if name == "google" else "мир"

    monkeypatch.setattr(tr, "_run_provider", fake)
    tr._cached.cache_clear()
    assert tr._cached("world", "en", "ru", "en-US", "ru-RU") == "мир"
    tr._cached.cache_clear()


def test_first_only_applies_to_words_not_phrases(monkeypatch):
    # on the practice path (allow_echo=True) single-word multi-candidate
    # answers pick the first candidate; phrases must survive intact
    monkeypatch.setenv("SPIIK_TRANSLATE", "online")

    def fake(name, text, src, dst, allow_echo=False):
        return tr.clean_translation(
            "мир, свет",
            text,
            allow_echo=allow_echo,
            first_only=allow_echo and " " not in text.strip(),
        )

    monkeypatch.setattr(tr, "_run_provider", fake)
    tr._cached.cache_clear()
    assert tr._cached("мир", "en", "ru", "en-US", "ru-RU", allow_echo=True) == "мир"
    tr._cached.cache_clear()
    assert (
        tr._cached("hello there", "en", "ru", "en-US", "ru-RU", allow_echo=True)
        == "мир, свет"
    )
    tr._cached.cache_clear()
