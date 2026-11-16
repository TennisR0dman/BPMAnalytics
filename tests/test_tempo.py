"""Tempo folding, bands, and the SQL CASE that restates the fold."""

import pytest

from bpm_analytics.tempo import (
    fold_tempo,
    octave_direction,
    octave_steps,
    sql_case_fold,
    tempo_band_key,
    tempo_band_label,
)


@pytest.mark.parametrize(
    ("bpm", "expected"),
    [
        (70, 70),
        (100, 100),
        (139.999, 139.999),
        (140, 70),
        (160, 80),
        (200, 100),
        (280, 70),
        (69, 138),
        (50, 100),
        (35, 70),
        (20, 80),
    ],
)
def test_fold_primary_window(bpm, expected):
    assert fold_tempo(bpm) == pytest.approx(expected)


def test_fold_rejects_unusable_values():
    assert fold_tempo(None) is None
    assert fold_tempo(0) is None
    assert fold_tempo(-10) is None
    assert fold_tempo(float("nan")) is None


def test_sql_case_matches_fold_across_catalog_range():
    bpm = 10.0
    while bpm < 500:
        assert sql_case_fold(bpm) == pytest.approx(fold_tempo(bpm))
        bpm += 0.5


def test_direction_and_steps():
    assert octave_direction(160, 80) == "halved"
    assert octave_direction(50, 100) == "doubled"
    assert octave_direction(100, 100) == "unshifted"
    assert octave_steps(280, 70) == 2
    assert octave_steps(100, 100) == 0


def test_band_edges():
    assert tempo_band_key(79.9) == 1
    assert tempo_band_key(80) == 2
    assert tempo_band_key(99.9) == 2
    assert tempo_band_key(100) == 3
    assert tempo_band_key(139.9) == 4
    assert tempo_band_key(140) == 5
    assert tempo_band_key(159.9) == 5
    assert tempo_band_key(160) == 6
    assert tempo_band_label(6) == "160 and above"
