"""Phonetics core tests: tokenizer, G2P, approximation, alignment, drills."""

from __future__ import annotations

import pytest

from app.core.align import align, score, verdicts
from app.core.approx import approximate
from app.core.drills import describe_sound
from app.core.g2p import get_g2p
from app.core.languages import list_languages, load_language
from app.core.tokenizer import tokenize_ipa


@pytest.fixture(scope="module")
def langs():
    return load_language("en-us"), load_language("pt-br")


@pytest.fixture(scope="module")
def g2p():
    return get_g2p()


def test_tokenize_multi_char_units():
    tokens = tokenize_ipa("kɹiːˈeɪʃən", inventory=["iː", "eɪ"])
    assert [t.ipa for t in tokens] == ["k", "ɹ", "iː", "eɪ", "ʃ", "ə", "n"]
    # espeak marks the stress before the stressed syllable's vowel (eɪ)
    assert tokens[3].stress == 1
    assert tokens[2].stress == 0


def test_tokenize_nasal_diacritic():
    tokens = tokenize_ipa("pˈɐ̃ʊ̃", inventory=["ɐ̃ʊ̃"])
    assert [t.ipa for t in tokens] == ["p", "ɐ̃ʊ̃"]


def test_g2p_creation(g2p, langs):
    en, _ = langs
    tokens = g2p.phonemize("creation", en)
    assert [t.ipa for t in tokens] == ["k", "ɹ", "iː", "eɪ", "ʃ", "ə", "n"]


def test_approximate_creation_pt(g2p, langs):
    en, pt = langs
    tokens = g2p.phonemize("creation", en)
    result = approximate(tokens, en, pt)
    assert result.text == "cri-ei-chan"
    # every chunk maps back to the word's phonemes
    assert sum(len(c.phonemes) for c in result.chunks) == len(tokens)
    missing = {m.ipa for m in result.missing_sounds}
    assert missing == {"iː", "ə"}


def test_approximate_think_pt(g2p, langs):
    en, pt = langs
    tokens = g2p.phonemize("think", en)
    result = approximate(tokens, en, pt)
    assert result.text == "sinc"
    missing = {m.ipa: m for m in result.missing_sounds}
    # θ is THE classic sound Portuguese lacks → major, not minor
    assert "θ" in missing and not missing["θ"].minor
    assert missing["θ"].substitute in ("t", "s")
    assert missing["θ"].substitute_display in ("t", "s")


def test_missing_sound_needs_training_flags(g2p, langs):
    en, pt = langs
    result = approximate(g2p.phonemize("this", en), en, pt)
    by_ipa = {m.ipa: m for m in result.missing_sounds}
    assert "ð" in by_ipa and not by_ipa["ð"].minor  # ð genuinely absent → training
    assert "ɪ" in by_ipa and by_ipa["ɪ"].minor  # close-ish substitute exists


def test_approximate_reverse_direction_pt_to_en(g2p, langs):
    en, pt = langs
    result = approximate(g2p.phonemize("pão", pt), pt, en)
    assert result.text == "pow"
    result = approximate(g2p.phonemize("ilha", pt), pt, en)
    assert "ly" in result.text


def test_native_display_substitutes_foreign_sounds(langs):
    _, pt = langs
    assert pt.native_display("θ") in ("t", "s")
    assert pt.native_display("ʃ") == "ch"


def test_align_identical_all_correct(langs):
    en, pt = langs
    pairs = align(["k", "æ", "t"], ["k", "æ", "t"])
    verdict_list = verdicts(pairs, en, pt)
    assert all(v.status == "correct" for v in verdict_list)
    assert score(3, verdict_list, 0) == 100


def test_align_near_miss_is_close(langs):
    en, pt = langs
    # Portuguese speaker says 'sink' for 'think'
    pairs = align(["θ", "ɪ", "ŋ", "k"], ["s", "i", "ŋ", "k"])
    verdict_list = verdicts(pairs, en, pt)
    by_expected = {v.expected: v for v in verdict_list}
    assert by_expected["θ"].status in ("close", "wrong")
    assert by_expected["θ"].recognized == "s"
    assert by_expected["ŋ"].status == "correct"


def test_align_missing_and_extra(langs):
    en, pt = langs
    # user skips the first sound and adds a trailing vowel
    pairs = align(["θ", "ɪ", "ŋ", "k"], ["ɪ", "ŋ", "k", "i"])
    verdict_list = verdicts(pairs, en, pt)
    by_expected = {v.expected: v for v in verdict_list}
    assert by_expected["θ"].status == "missing"
    assert any(p.expected is None and p.recognized == "i" for p in pairs)


def test_score_bounds():
    assert 0 <= score(4, [], 10) <= 100


def test_describe_sound():
    assert describe_sound("θ") == "voiceless dental fricative"
    assert "vowel" in describe_sound("y")


def test_all_language_files_load():
    codes = ["en-us", "pt-br", "es", "de", "fr-fr", "it", "ru", "th"]
    for code in codes:
        lang = load_language(code)
        assert lang.inventory, code
        assert lang.orthography, code
        # every inventory sound should have a native spelling
        for sound in lang.inventory:
            assert sound in lang.orthography, f"{code}: {sound} has no orthography"


def test_approximate_english_for_russian_learners(g2p, langs):
    en, _ = langs
    ru = load_language("ru")
    # Russians render these words exactly this way when writing English by ear
    cases = {
        "think": "сингк",
        "day": "дэй",
        "house": "хаус",
        "king": "кинг",
        "jazz": "джэз",
        "yes": "йэс",
    }
    for word, expected in cases.items():
        result = approximate(g2p.phonemize(word, en), en, ru)
        assert result.text == expected, f"{word}: {result.text!r} != {expected!r}"
    # θ and w are the classic trouble sounds for Russian speakers
    think_missing = {m.ipa for m in approximate(g2p.phonemize("think", en), en, ru).missing_sounds}
    assert "θ" in think_missing
    world_missing = {m.ipa: m for m in approximate(g2p.phonemize("world", en), en, ru).missing_sounds}
    assert "w" in world_missing and world_missing["w"].substitute == "v"


def test_approximate_russian_for_english_learners(g2p, langs):
    _, _ = langs
    en = load_language("en-us")
    ru = load_language("ru")
    result = approximate(g2p.phonemize("привет", ru), ru, en)
    assert result.text == "pryi-vyet"
    missing = {m.ipa for m in result.missing_sounds}
    # the trill and palatalization are the sounds English speakers must train
    assert "r" in missing and "ʲ" in missing


def test_russian_stress_marks_tokenize(g2p, langs):
    ru = load_language("ru")
    tokens = g2p.phonemize("вода", ru)
    # espeak marks ɑ (stressed а) with "; no raw " or ^ tokens may leak through
    assert all(t.ipa not in ('"', "^") for t in tokens)
    assert [t.ipa for t in tokens] == ["v", "ʌ", "d", "ɑ"]
    assert tokens[-1].stress == 1


def test_translate_word_uses_provider_chain(monkeypatch, langs):
    import app.translate as tr

    en, pt = load_language("en-us"), load_language("pt-br")
    # first provider fails, second supplies the translation
    monkeypatch.setattr(
        tr,
        "_run_provider",
        lambda name, text, s, d, allow_echo=False: None if name == "google" else "Criação",
    )
    tr._cached.cache_clear()
    assert tr.translate_word("creation", en, pt) == "Criação"


def test_translate_word_returns_none_when_all_providers_fail(monkeypatch, langs):
    import app.translate as tr

    en, ru = langs
    monkeypatch.setattr(tr, "_run_provider", lambda name, text, s, d, allow_echo=False: None)
    tr._cached.cache_clear()
    assert tr.translate_word("zzzq", en, ru) is None
    tr._cached.cache_clear()


def test_translate_word_strips_punctuation_artifacts(langs):
    import app.translate as tr

    en, ru = langs
    assert tr.clean_translation("мир,", "world") == "мир"
    assert tr.clean_translation("Спасибо.", "thank you") == "Спасибо"
    # an echo of the input is not a translation
    assert tr.clean_translation("world", "world") is None
    assert tr.clean_translation(None, "world") is None


def test_every_language_has_translation_codes():
    for lang in list_languages():
        codes = lang.translate
        assert "google" in codes and "mymemory" in codes, lang.code


def test_approximate_english_for_thai_learners(g2p, langs):
    en, _ = langs
    th = load_language("th")
    cases = {
        "think": "ซิงก",
        "this": "ดิส",
        "king": "กิง",
    }
    for word, expected in cases.items():
        result = approximate(g2p.phonemize(word, en), en, th)
        assert result.text == expected, f"{word}: {result.text!r} != {expected!r}"
    think_missing = {m.ipa for m in approximate(g2p.phonemize("think", en), en, th).missing_sounds}
    assert "θ" in think_missing


def test_approximate_thai_for_english_learners(g2p, langs):
    _, _ = langs
    en = load_language("en-us")
    th = load_language("th")
    result = approximate(g2p.phonemize("กิน", th), th, en)
    assert result.text == "kin"


def test_thai_tone_marks_tokenize(g2p, langs):
    th = load_language("th")
    tokens = g2p.phonemize("กิน", th)
    # espeak marks tone with ASCII digits (e.g. 2); no raw digits may leak through
    assert all(not t.ipa.isdigit() for t in tokens)
    assert [t.ipa for t in tokens] == ["k", "i", "n"]


def test_align_thai_pronunciation():
    th = load_language("th")
    en = load_language("en-us")
    pairs = align(["k", "i", "n"], ["k", "i", "n"])
    verdict_list = verdicts(pairs, th, en)
    assert all(v.status == "correct" for v in verdict_list)
    assert score(3, verdict_list, 0) == 100

