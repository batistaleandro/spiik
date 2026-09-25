"""Community pronunciation feedback: alternative suggestions and votes.

Resolution rules:
- The system-generated pronunciation has a neutral 0.5 approval rate until
  someone votes on it; a suggestion with no votes has rate 0 (no evidence)
  and never promotes.
- A suggestion becomes the default when its approval rate strictly surpasses
  the system rate. Ties between suggestions go to the one with more votes,
  then the earliest.
- Until promoted, a suggestion is only effective for its author and the users
  sampled into its audience at creation time. A promoted suggestion is
  effective for everyone — and slips back to the system one if the system
  rate later rises above it again.

Suggestions only change the displayed approximation text; the expected IPA
used for speech assessment and the SRS state stay system-generated.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    PronunciationSuggestion,
    PronunciationSystemVote,
    PronunciationVote,
    User,
)


def key_for(native: str, target: str, word: str) -> tuple[str, str, str]:
    """Community key for a word: casefolded language pair + word text."""
    return (native.casefold(), target.casefold(), word.casefold())


def _rate(up: int, down: int, neutral: float) -> float:
    total = up + down
    return up / total if total else neutral


def resolve_pronunciation(
    db: Session,
    user: User,
    native: str,
    target: str,
    text: str,
    system_approx: str | None = None,
) -> dict:
    """Resolve the effective pronunciation of a single word for one user."""
    items = [(native, target, text, system_approx)]
    return resolve_pronunciation_batch(db, user, items)[key_for(native, target, text)]


def resolve_pronunciation_batch(
    db: Session,
    user: User,
    items: list[tuple[str, str, str, str | None]],
) -> dict[tuple[str, str, str], dict]:
    """Resolve the effective pronunciation for several words at once.

    `items` are `(native, target, word_text, system_approximation)` tuples.
    Returns a dict keyed by `key_for(native, target, word_text)`.
    """
    display_text: dict[tuple[str, str, str], str] = {}
    system_approx: dict[tuple[str, str, str], str | None] = {}
    for native, target, word, approx in items:
        key = key_for(native, target, word)
        if key not in display_text:
            display_text[key] = word
            system_approx[key] = approx
        elif system_approx[key] is None and approx is not None:
            system_approx[key] = approx
    if not display_text:
        return {}

    folded_words = list({key[2] for key in display_text})

    suggestions = [
        s
        for s in db.scalars(
            select(PronunciationSuggestion).where(
                PronunciationSuggestion.word_text.in_(folded_words)
            )
        ).all()
        if (s.native_lang.casefold(), s.target_lang.casefold(), s.word_text)
        in display_text
    ]

    suggestion_ids = [s.id for s in suggestions]
    votes_by_suggestion: dict[int, list[PronunciationVote]] = {}
    if suggestion_ids:
        for v in db.scalars(
            select(PronunciationVote).where(
                PronunciationVote.suggestion_id.in_(suggestion_ids)
            )
        ).all():
            votes_by_suggestion.setdefault(v.suggestion_id, []).append(v)

    sys_votes_by_key: dict[tuple[str, str, str], list[PronunciationSystemVote]] = {}
    for v in db.scalars(
        select(PronunciationSystemVote).where(
            PronunciationSystemVote.word_text.in_(folded_words)
        )
    ).all():
        sys_votes_by_key.setdefault(key_for(v.native_lang, v.target_lang, v.word_text), []).append(v)

    return {
        key: _resolve_one(
            user,
            key,
            display_text[key],
            system_approx[key],
            [s for s in suggestions if (s.native_lang.casefold(), s.target_lang.casefold(), s.word_text) == key],
            votes_by_suggestion,
            sys_votes_by_key.get(key, []),
        )
        for key in display_text
    }


def _resolve_one(
    user: User,
    key: tuple[str, str, str],
    word_text: str,
    system_approx: str | None,
    suggestions: list[PronunciationSuggestion],
    votes_by_suggestion: dict[int, list[PronunciationVote]],
    sys_votes: list[PronunciationSystemVote],
) -> dict:
    sys_up = sum(1 for v in sys_votes if v.vote == "up")
    sys_down = len(sys_votes) - sys_up
    my_sys_vote = next((v.vote for v in sys_votes if v.user_id == user.id), None)
    system_rate = _rate(sys_up, sys_down, neutral=0.5)

    # (suggestion, rate, total_votes, payload) per suggestion
    rows = []
    for s in suggestions:
        votes = votes_by_suggestion.get(s.id, [])
        up = sum(1 for v in votes if v.vote == "up")
        down = len(votes) - up
        rows.append(
            (
                s,
                _rate(up, down, neutral=0.0),
                up + down,
                {
                    "id": s.id,
                    "text": s.suggested_text,
                    "up": up,
                    "down": down,
                    "rate": round(_rate(up, down, neutral=0.0), 4),
                    "my_vote": next((v.vote for v in votes if v.user_id == user.id), None),
                    "mine": s.author_id == user.id,
                    "in_audience": user.id in (s.audience or []),
                    "promoted": False,
                },
            )
        )

    effective: dict | None = None
    promoted = [r for r in rows if r[1] > system_rate]
    if promoted:
        # highest approval rate wins; ties by most votes, then earliest
        promoted.sort(key=lambda r: (-r[1], -r[2], r[0].created_at, r[0].id))
        s = promoted[0][0]
        promoted[0][3]["promoted"] = True
        effective = {"source": "suggestion", "text": s.suggested_text, "suggestion_id": s.id}
    else:
        # not promoted: only the author and sampled audience members see a
        # suggestion instead of the system one
        targeted = [r for r in rows if r[3]["mine"] or r[3]["in_audience"]]
        if targeted:
            targeted.sort(key=lambda r: (-r[1], -r[2], -r[0].id))
            s = targeted[0][0]
            effective = {"source": "suggestion", "text": s.suggested_text, "suggestion_id": s.id}
    if effective is None:
        effective = {"source": "system", "text": system_approx, "suggestion_id": None}

    return {
        "native": key[0],
        "target": key[1],
        "text": word_text,
        "system": {"up": sys_up, "down": sys_down, "my_vote": my_sys_vote},
        "suggestions": [r[3] for r in rows],
        "effective": effective,
    }
