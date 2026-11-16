"""Tempo from a local preview file.

librosa.beat.beat_track is the primary estimate. librosa.feature.tempo is
kept as a second reading. Neither number is a producer-entered BPM.
"""

from __future__ import annotations

import math


def _as_bpm(value):
    if value is None:
        return None
    if hasattr(value, "reshape"):
        flat = [float(item) for item in value.reshape(-1)]
        flat = [item for item in flat if math.isfinite(item) and item > 0]
        if not flat:
            return None
        value = flat[0]
    try:
        tempo = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(tempo) or tempo <= 0:
        return None
    return tempo


def estimate_bpm(path: str) -> dict:
    """Estimate BPM from an audio file that is already on disk."""
    import librosa

    samples, sample_rate = librosa.load(path, sr=22050, mono=True)
    if samples is None or len(samples) < sample_rate:
        return {"librosa_bpm": None, "librosa_tempo_bpm": None, "librosa_method": "too_short"}
    beat_tempo, _beats = librosa.beat.beat_track(y=samples, sr=sample_rate)
    feature_tempo = librosa.feature.tempo(y=samples, sr=sample_rate)
    beat_bpm = _as_bpm(beat_tempo)
    feature_bpm = _as_bpm(feature_tempo)
    if beat_bpm is not None:
        method = "beat_track"
        chosen = beat_bpm
    elif feature_bpm is not None:
        method = "feature_tempo"
        chosen = feature_bpm
    else:
        method = "failed"
        chosen = None
    return {
        "librosa_bpm": chosen,
        "librosa_tempo_bpm": feature_bpm,
        "librosa_method": method,
    }
