"""Alignment of expected vs recognized phoneme sequences.

Needleman-Wunsch over feature-weighted distances: /θ/ recognized as /s/ is a
near miss, /θ/ as /m/ a far miss. Produces per-phoneme verdicts for the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.languages import Language, segment_distance

GAP_COST = 0.75

# distance thresholds for verdicts
CLOSE_DISTANCE = 0.5
FAR_DISTANCE = 1.25


@dataclass
class AlignedPair:
    expected: str | None  # target-language phoneme (None = extra from user)
    recognized: str | None  # what the user actually said (None = missing)
    distance: float  # 0.0 when both None-ness matches (never happens)

    def to_dict(self) -> dict:
        return {"expected": self.expected, "recognized": self.recognized, "distance": self.distance}


def align(expected: list[str], recognized: list[str]) -> list[AlignedPair]:
    n, m = len(expected), len(recognized)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int]]] = [[(0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP_COST
        back[i][0] = (i - 1, 0)
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP_COST
        back[0][j] = (0, j - 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = dp[i - 1][j - 1] + segment_distance(expected[i - 1], recognized[j - 1])
            dele = dp[i - 1][j] + GAP_COST
            ins = dp[i][j - 1] + GAP_COST
            best, where = min((sub, (i - 1, j - 1)), (dele, (i - 1, j)), (ins, (i, j - 1)))
            dp[i][j] = best
            back[i][j] = where

    pairs: list[AlignedPair] = []
    i, j = n, m
    while (i, j) != (0, 0):
        pi, pj = back[i][j]
        if pi == i - 1 and pj == j - 1:
            pairs.append(AlignedPair(expected[i - 1], recognized[j - 1], segment_distance(expected[i - 1], recognized[j - 1])))
        elif pi == i - 1:
            pairs.append(AlignedPair(expected[i - 1], None, GAP_COST))
        else:
            pairs.append(AlignedPair(None, recognized[j - 1], GAP_COST))
        i, j = pi, pj
    pairs.reverse()
    return pairs


@dataclass
class PhonemeVerdict:
    expected: str
    recognized: str | None
    status: str  # correct | close | wrong | missing
    distance: float
    hint: str  # explanation in the learner's language orthography
    foreign: bool = False  # expected sound doesn't exist in the learner's language

    def to_dict(self) -> dict:
        return {
            "expected": self.expected,
            "recognized": self.recognized,
            "status": self.status,
            "distance": self.distance,
            "hint": self.hint,
            "foreign": self.foreign,
        }


def _hint_for(expected: str, recognized: str | None, target: Language, native: Language) -> str:
    foreign = expected not in native.inventory
    if recognized is None:
        if foreign:
            return f"the {target.name} sound /{expected}/ was skipped — see the drill below"
        return f"the “{native.orthography.get(expected, expected)}” sound was skipped"
    if recognized == expected:
        return "correct"
    rec_disp = native.native_display(recognized)
    if foreign:
        substitute, _ = native.closest_sound(expected)
        if recognized == substitute:
            return (
                f"you said the approximation “{rec_disp}” — now train the real "
                f"{target.name} sound /{expected}/ with the drill"
            )
        return (
            f"you said “{rec_disp}” — the target sound is /{expected}/, "
            f"which does not exist in {native.name} — see the drill"
        )
    exp_disp = native.orthography.get(expected, expected)
    return f"you said “{rec_disp}” — the correct sound is “{exp_disp}”"


def verdicts(pairs: list[AlignedPair], target: Language, native: Language) -> list[PhonemeVerdict]:
    out: list[PhonemeVerdict] = []
    for pair in pairs:
        if pair.expected is None:
            continue  # extra sounds are reported via extras count, not verdicts
        if pair.recognized is None:
            status = "missing"
        elif pair.distance <= 0.0:
            status = "correct"
        elif pair.distance <= CLOSE_DISTANCE:
            status = "close"
        else:
            status = "wrong"
        out.append(
            PhonemeVerdict(
                expected=pair.expected,
                recognized=pair.recognized,
                status=status,
                distance=round(pair.distance, 3),
                hint=_hint_for(pair.expected, pair.recognized, target, native),
                foreign=pair.expected not in native.inventory,
            )
        )
    return out


def score(expected_count: int, verdict_list: list[PhonemeVerdict], extras: int) -> int:
    """0–100 overall score from the per-phoneme verdicts."""
    if expected_count == 0:
        return 0
    total = 0.0
    for v in verdict_list:
        if v.status == "correct":
            total += 1.0
        elif v.status == "close":
            total += 0.6
        # wrong / missing contribute 0
    penalty = 0.25 * extras
    return max(0, min(100, round(100 * max(0.0, total - penalty) / expected_count)))
