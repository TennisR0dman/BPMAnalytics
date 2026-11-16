"""librosa tempo on a synthetic click track. No chart pages and no Deezer."""

from pathlib import Path

import numpy as np
import soundfile as sf

from bpm_analytics.bpm_audio import estimate_bpm


def _write_clicks(path: Path, bpm: float, seconds: float = 16.0, sample_rate: int = 22050) -> None:
    count = int(seconds * sample_rate)
    samples = np.zeros(count, dtype=np.float32)
    step = int(sample_rate * 60.0 / bpm)
    click = np.hanning(180).astype(np.float32)
    for start in range(0, count - len(click), step):
        samples[start : start + len(click)] += click
    sf.write(path, samples, sample_rate)


def test_click_track_lands_on_the_tempo_or_its_octave(tmp_path):
    path = tmp_path / "clicks.wav"
    _write_clicks(path, 120)
    estimated = estimate_bpm(str(path))
    assert estimated["librosa_bpm"] is not None
    ratio = estimated["librosa_bpm"] / 120.0
    assert any(abs(ratio - target) < 0.12 for target in (0.5, 1.0, 2.0))
