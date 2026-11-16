"""Checks against the files the pipeline writes. Skips locally if it has not been run."""

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from bpm_analytics.config import (
    DATA_PROCESSED,
    RESULTS_PATH,
    ROOT,
    STAR_DIR,
)
from bpm_analytics.cohorts import load_lookup
from bpm_analytics.tempo import fold_tempo, sql_case_fold

README = ROOT / "README.md"
AUDIT = ROOT / "outputs" / "sql" / "06_afrobeat_label_audit.csv"
SUMMARY = ROOT / "outputs" / "sql" / "01_cohort_summary.csv"


def _need(path: Path):
    if path.exists():
        return
    if os.environ.get("CI"):
        pytest.fail(f"Missing pipeline output in CI: {path}")
    pytest.skip(f"Pipeline output not built: {path}")


def test_headline_cohorts_are_disjoint_and_full():
    _need(DATA_PROCESSED)
    frame = pd.read_csv(DATA_PROCESSED)
    top = frame[frame["is_top100"] == 1]
    counts = top["cohort_id"].value_counts().to_dict()
    assert counts.get("africa_popular") == 100
    assert counts.get("us_hiphop_genre") == 100
    africa_ids = set(top.loc[top["cohort_id"] == "africa_popular", "track_id"])
    hiphop_ids = set(top.loc[top["cohort_id"] == "us_hiphop_genre", "track_id"])
    assert africa_ids.isdisjoint(hiphop_ids)

    lookup = load_lookup(ROOT / "data" / "reference" / "african_primary_artists.csv")
    keys = set(lookup["name_key"])
    africa = frame[frame["cohort_id"] == "africa_popular"]
    hiphop = frame[frame["cohort_id"] == "us_hiphop_genre"]
    assert set(africa["primary_artist"].str.casefold()).issubset(keys)
    assert set(hiphop["primary_artist"].str.casefold()).isdisjoint(keys)
    assert set(hiphop["track_genre"]) == {"hip-hop"}
    assert "Calle 13" not in set(frame["primary_artist"])
    assert (africa["country"].fillna("") != "").all()
    assert (hiphop["country"].fillna("") == "").all()

    for raw, corrected in zip(frame["tempo_raw"], frame["tempo_corrected"]):
        assert 70 <= corrected < 140
        assert sql_case_fold(raw) == pytest.approx(corrected, abs=1e-4)
        assert fold_tempo(raw) == pytest.approx(corrected, abs=1e-4)


def test_label_audit_shows_the_afrobeat_tag_is_not_the_cohort():
    _need(AUDIT)
    audit = pd.read_csv(AUDIT)
    assert len(audit) == 25
    calle = audit[audit["primary_artist"] == "Calle 13"]
    assert not calle.empty
    assert set(calle["on_african_lookup"]) == {0}
    assert audit["on_african_lookup"].sum() < 10


def test_sql_medians_match_the_r_report():
    _need(SUMMARY)
    _need(RESULTS_PATH)
    summary = pd.read_csv(SUMMARY)
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    for _, row in summary.iterrows():
        published = results["cohorts"][row["cohort_id"]]
        assert row["n_tracks"] == published["n_top"]
        assert row["median_raw"] == pytest.approx(published["tempo_raw_median"], abs=1e-4)
        assert row["mean_raw"] == pytest.approx(published["tempo_raw_mean"], abs=1e-4)
        assert row["sd_raw"] == pytest.approx(published["tempo_raw_sd"], abs=1e-4)


def test_star_schema_keys_resolve():
    _need(STAR_DIR / "fact_track.csv")
    fact = pd.read_csv(STAR_DIR / "fact_track.csv")
    cohort = pd.read_csv(STAR_DIR / "dim_cohort.csv")
    artist = pd.read_csv(STAR_DIR / "dim_artist.csv")
    track = pd.read_csv(STAR_DIR / "dim_track.csv")
    band = pd.read_csv(STAR_DIR / "dim_tempo_band.csv")
    analysis = pd.read_csv(DATA_PROCESSED)
    assert len(fact) == len(analysis)
    assert fact["track_key"].is_unique
    assert set(fact["cohort_key"]).issubset(set(cohort["cohort_key"]))
    assert set(fact["artist_key"]).issubset(set(artist["artist_key"]))
    assert set(fact["track_key"]).issubset(set(track["track_key"]))
    assert set(fact["raw_band_key"]).issubset(set(band["band_key"]))
    assert set(fact["corrected_band_key"]).issubset(set(band["band_key"]))
    assert set(cohort["cohort_id"]) == {"africa_popular", "us_hiphop_genre"}


def test_readme_quotes_the_published_lines():
    _need(RESULTS_PATH)
    _need(README)
    _need(SUMMARY)
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8")
    missing = [text for text in results["display"].values() if text not in readme]
    assert not missing, missing
    summary = pd.read_csv(SUMMARY)
    for value in summary["mean_popularity"]:
        assert f"{value:.1f}" in readme


def test_figures_exist():
    _need(RESULTS_PATH)
    for name in (
        "01_tempo_density_raw.png",
        "02_tempo_density_corrected.png",
        "03_tempo_band_share.png",
        "04_popularity_by_band.png",
    ):
        path = ROOT / "outputs" / "figures" / name
        assert path.exists(), name
        assert path.stat().st_size > 10_000
