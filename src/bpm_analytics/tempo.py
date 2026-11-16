"""Tempo octave folding and tempo-band labels.

Spotify's tempo is an estimate from the audio, not a producer-entered BPM.
The estimator often locks onto half or double the pulse a listener counts,
especially on rap drums. `fold_tempo` walks that estimate into a window by
halving or doubling. It does not claim the folded value is the true tempo.
"""

from __future__ import annotations

import math

from bpm_analytics.config import BANDS, FOLD_HIGH, FOLD_LOW


def fold_tempo(bpm, low: float = FOLD_LOW, high: float = FOLD_HIGH):
    """Return bpm folded into [low, high), or None when bpm is unusable.

    At most six octave steps are applied. The upper bound is exclusive, so
    140 with the default window becomes 70 (a common double-time rap tag).
    """
    if bpm is None:
        return None
    try:
        tempo = float(bpm)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(tempo) or tempo <= 0:
        return None
    for _ in range(6):
        if tempo >= high:
            tempo = tempo / 2.0
        elif tempo < low:
            tempo = tempo * 2.0
        else:
            break
    return tempo


def octave_steps(raw, corrected) -> int:
    """How many halvings or doublings separate the raw and folded tempos."""
    if raw is None or corrected is None:
        return 0
    raw = float(raw)
    corrected = float(corrected)
    if raw <= 0 or corrected <= 0:
        return 0
    ratio = max(raw, corrected) / min(raw, corrected)
    # ratio is a power of two when the fold only halves or doubles
    steps = 0
    while ratio > 1.5 and steps < 6:
        ratio = ratio / 2.0
        steps += 1
    return steps


def octave_direction(raw, corrected) -> str:
    if raw is None or corrected is None:
        return "unresolved"
    if abs(float(corrected) - float(raw)) < 1e-6:
        return "unshifted"
    if float(corrected) < float(raw):
        return "halved"
    return "doubled"


def tempo_band_key(bpm) -> int | None:
    """Band key 1-6. Boundaries sit on the higher band: 80 is '80-99'."""
    if bpm is None:
        return None
    try:
        tempo = float(bpm)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(tempo):
        return None
    for key, _label, low, high in BANDS:
        if high is None:
            if tempo >= low:
                return key
        elif low <= tempo < high:
            return key
    return None


def tempo_band_label(key: int | None) -> str | None:
    if key is None:
        return None
    for band_key, label, _low, _high in BANDS:
        if band_key == key:
            return label
    return None


def sql_case_fold(bpm: float) -> float:
    """Octave fold as a SQL CASE can express it, for the primary window.

    Equivalent to `fold_tempo` for tempos from 8.75 BPM up to 1120 BPM,
    which covers this catalog. The integration test checks every analysis row.
    """
    tempo = float(bpm)
    if tempo >= 560:
        return tempo / 8.0
    if tempo >= 280:
        return tempo / 4.0
    if tempo >= 140:
        return tempo / 2.0
    if tempo < 17.5:
        return tempo * 8.0
    if tempo < 35:
        return tempo * 4.0
    if tempo < 70:
        return tempo * 2.0
    return tempo
