"""The summary SQL median and the afrobeat label audit run on a tiny warehouse."""

import sqlite3
from pathlib import Path

import pandas as pd

from bpm_analytics.config import ROOT

SQL = ROOT / "sql"


def _connect():
    conn = sqlite3.connect(":memory:")
    conn.executescript((SQL / "00_schema.sql").read_text(encoding="utf-8"))
    return conn


def _analysis_row(**overrides):
    base = {
        "cohort_id": "africa_popular",
        "cohort_name": "African popular music",
        "track_id": "t",
        "track_name": "Song",
        "artists": "Artist",
        "album_name": "Album",
        "primary_artist": "Artist",
        "country": "Nigeria",
        "region": "West Africa",
        "scene": "afrobeats",
        "track_genre": "dancehall",
        "popularity": 50,
        "popularity_rank": 1,
        "is_top100": 1,
        "duration_ms": 200000,
        "explicit": 0,
        "tempo_raw": 100.0,
        "tempo_corrected": 100.0,
        "tempo_corrected_alt": 100.0,
        "octave_shifts": 0,
        "octave_direction": "unshifted",
        "octave_shifted": 0,
        "raw_band_key": 3,
        "raw_band": "100-119",
        "corrected_band_key": 3,
        "corrected_band": "100-119",
        "danceability": 0.5,
        "energy": 0.5,
        "valence": 0.5,
        "speechiness": 0.1,
        "acousticness": 0.1,
        "loudness": -8.0,
        "time_signature": 4,
    }
    base.update(overrides)
    return base


def test_summary_median_mean_and_sample_sd():
    conn = _connect()
    rows = [
        _analysis_row(track_id="a", tempo_raw=10, tempo_corrected=10, popularity=40),
        _analysis_row(track_id="b", tempo_raw=20, tempo_corrected=20, popularity=50),
        _analysis_row(track_id="c", tempo_raw=30, tempo_corrected=30, popularity=60),
        _analysis_row(track_id="d", tempo_raw=40, tempo_corrected=40, popularity=70),
        _analysis_row(
            track_id="hidden",
            tempo_raw=1000,
            tempo_corrected=1000,
            popularity=10,
            is_top100=0,
            popularity_rank=5,
        ),
    ]
    frame = pd.DataFrame(rows)
    frame.to_sql("track_analysis", conn, if_exists="append", index=False)
    summary = pd.read_sql_query((SQL / "01_cohort_summary.sql").read_text(encoding="utf-8"), conn)
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["n_tracks"] == 4
    assert row["median_raw"] == 25
    assert row["mean_raw"] == 25
    # Sample sd of 10, 20, 30, 40. Population second moment would divide by 4.
    deviations = sum((value - 25) ** 2 for value in (10, 20, 30, 40))
    expected_sd = (deviations / 3) ** 0.5
    assert row["sd_raw"] == pytest_approx(expected_sd)
    assert row["min_popularity"] == 40
    assert row["max_popularity"] == 70


def test_octave_query_flags_half_and_double_time():
    conn = _connect()
    rows = [
        _analysis_row(track_id="fast", tempo_raw=160, tempo_corrected=80, octave_direction="halved", octave_shifted=1, octave_shifts=1),
        _analysis_row(track_id="slow", tempo_raw=50, tempo_corrected=100, octave_direction="doubled", octave_shifted=1, octave_shifts=1),
    ]
    pd.DataFrame(rows).to_sql("track_analysis", conn, if_exists="append", index=False)
    folded = pd.read_sql_query((SQL / "03_octave_correction.sql").read_text(encoding="utf-8"), conn)
    directions = dict(zip(folded["octave_direction"], folded["mean_folded_sql"]))
    assert directions["halved"] == pytest_approx(80)
    assert directions["doubled"] == pytest_approx(100)


def test_afrobeat_audit_flags_lookup_names_only():
    conn = _connect()
    conn.execute(
        "INSERT INTO artist_lookup (artist_name, country, region, scene) VALUES (?, ?, ?, ?)",
        ("Fela Kuti", "Nigeria", "West Africa", "afrobeat"),
    )
    catalog_rows = [
        ("c1", "Atrévete", "Calle 13", "x", "Calle 13", 75, 180000, 0, 88.0, 4, "afrobeat", 0.8, 0.8, 0.7, 0.1, 0.2, -5.0),
        ("f1", "Zombie", "Fela Kuti", "x", "Fela Kuti", 48, 700000, 0, 120.0, 4, "afrobeat", 0.7, 0.7, 0.6, 0.2, 0.3, -7.0),
        ("p1", "Not This Genre", "Fela Kuti", "x", "Fela Kuti", 90, 200000, 0, 100.0, 4, "pop", 0.5, 0.5, 0.5, 0.1, 0.1, -6.0),
    ]
    conn.executemany(
        """
        INSERT INTO tracks_catalog (
            track_id, track_name, artists, album_name, primary_artist, popularity,
            duration_ms, explicit, tempo, time_signature, track_genre, danceability,
            energy, valence, speechiness, acousticness, loudness
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        catalog_rows,
    )
    conn.commit()
    audit = pd.read_sql_query((SQL / "06_afrobeat_label_audit.sql").read_text(encoding="utf-8"), conn)
    flagged = dict(zip(audit["primary_artist"], audit["on_african_lookup"]))
    assert flagged["Calle 13"] == 0
    assert flagged["Fela Kuti"] == 1
    assert "Not This Genre" not in set(audit["track_name"])


def test_sql_files_are_single_statements():
    for path in sorted(SQL.glob("[0-9][0-9]_*.sql")):
        if path.name.startswith("00_"):
            continue
        text = path.read_text(encoding="utf-8")
        stripped = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
        assert stripped.count(";") == 1, path.name


def pytest_approx(value):
    from pytest import approx

    return approx(value)
