"""Power BI star-schema extracts.

Grain of fact_track: one eligible track in one cohort.
Tempo band is a role-playing dimension: raw_band_key is the active
relationship, corrected_band_key is the second role.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bpm_analytics.config import AFRICA_COHORT, BANDS, COHORT_NAMES, HIPHOP_COHORT, ROOT

CHART_ANALYSIS_PATH = ROOT / "data" / "current" / "chart_analysis.csv"
AFRICA_CHARTS = "africa_charts"
US_CHART = "us_rb_hiphop_chart"

COHORT_ROWS = (
    (
        1,
        AFRICA_COHORT,
        COHORT_NAMES[AFRICA_COHORT],
        "africa",
        "Primary artist is on the African-scene lookup. Popularity is at least 40. "
        "is_top100 marks the 100 highest-popularity tracks. Not a country chart.",
    ),
    (
        2,
        HIPHOP_COHORT,
        COHORT_NAMES[HIPHOP_COHORT],
        "hiphop",
        "track_genre is hip-hop and the primary artist is not on the African-scene lookup. "
        "Popularity is at least 40. Genre proxy only: the file has no US chart flag.",
    ),
    (
        3,
        AFRICA_CHARTS,
        "Nigeria and South Africa Spotify charts",
        "africa",
        "Top 50 of the Kworb Spotify daily chart for Nigeria plus the top 50 for South Africa. "
        "Chart market is where the track ranked, not the artist's origin.",
    ),
    (
        4,
        US_CHART,
        "Billboard Hot R&B/Hip-Hop Songs",
        "hiphop",
        "Current Billboard Hot R&B/Hip-Hop Songs. The list mixes rap and R&B. "
        "It is a US chart, not a verified artist-origin list.",
    ),
)

SNAPSHOT_ROWS = (
    (
        1,
        "spotify_dataset",
        "Spotify tracks dataset",
        "Dataset card updated 2023-12-01; the pull date is not stated",
        "Genre labels and an artist lookup on the pinned Spotify tracks file.",
    ),
    (
        2,
        "current_charts",
        "Current charts",
        "Nigeria Spotify daily 2026-11-14; South Africa Spotify daily 2026-11-13; Billboard week of November 14, 2026. Pages fetched 2026-11-16.",
        "Tempo is measured with librosa on a Deezer 30-second preview.",
    ),
)


def _with_dataset_snapshot(analysis: pd.DataFrame) -> pd.DataFrame:
    frame = analysis.copy()
    frame["snapshot_id"] = "spotify_dataset"
    frame["comparison_arm"] = frame["cohort_id"].map({AFRICA_COHORT: "africa", HIPHOP_COHORT: "hiphop"})
    frame["chart_market"] = ""
    frame["chart_position"] = pd.NA
    frame["deezer_bpm"] = pd.NA
    return frame


def _chart_frame(path: Path) -> pd.DataFrame:
    charts = pd.read_csv(path)
    charts["snapshot_id"] = "current_charts"
    charts["popularity"] = pd.NA
    charts["popularity_rank"] = pd.NA
    charts["duration_ms"] = pd.NA
    charts["explicit"] = pd.NA
    charts["track_genre"] = ""
    charts["country"] = ""
    charts["region"] = ""
    charts["scene"] = ""
    for column in ("danceability", "energy", "valence", "speechiness", "acousticness", "loudness", "time_signature"):
        charts[column] = pd.NA
    return charts


def write_star(analysis: pd.DataFrame, out_dir: Path) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    combined = _with_dataset_snapshot(analysis)
    if CHART_ANALYSIS_PATH.exists():
        combined = pd.concat([combined, _chart_frame(CHART_ANALYSIS_PATH)], ignore_index=True)
    dim_cohort = pd.DataFrame(
        [
            {
                "cohort_key": key,
                "cohort_id": cohort_id,
                "cohort_name": name,
                "comparison_arm": arm,
                "definition": definition,
            }
            for key, cohort_id, name, arm, definition in COHORT_ROWS
        ]
    )
    dim_snapshot = pd.DataFrame(
        [
            {
                "snapshot_key": key,
                "snapshot_id": snapshot_id,
                "snapshot_name": name,
                "as_of_label": as_of,
                "definition": definition,
            }
            for key, snapshot_id, name, as_of, definition in SNAPSHOT_ROWS
        ]
    )
    dim_tempo_band = pd.DataFrame(
        [
            {
                "band_key": key,
                "band_label": label,
                "bpm_min": int(low),
                "bpm_max_exclusive": int(high) if high is not None else 9999,
                "sort_order": key,
            }
            for key, label, low, high in BANDS
        ]
    )

    artists = (
        combined[["primary_artist", "country", "region", "scene", "cohort_id"]]
        .copy()
        .sort_values(["primary_artist", "cohort_id"], kind="mergesort")
    )
    # One artist row. African lookup values win when the name is in that cohort.
    artists["_prefer"] = (artists["cohort_id"] != AFRICA_COHORT).astype(int)
    artists = artists.sort_values(["primary_artist", "_prefer"], kind="mergesort")
    artists = artists.drop_duplicates("primary_artist", keep="first").drop(columns=["_prefer", "cohort_id"])
    artists = artists.sort_values("primary_artist", kind="mergesort").reset_index(drop=True)
    artists.insert(0, "artist_key", range(1, len(artists) + 1))
    for col in ("country", "region", "scene"):
        artists[col] = artists[col].fillna("")
    dim_artist = artists

    tracks = combined.sort_values(["snapshot_id", "cohort_id", "track_id"], kind="mergesort").copy()
    tracks.insert(0, "track_key", range(1, len(tracks) + 1))
    dim_track = tracks[
        [
            "track_key",
            "track_id",
            "track_name",
            "artists",
            "album_name",
            "primary_artist",
            "duration_ms",
            "explicit",
            "track_genre",
        ]
    ].copy()

    fact = tracks.merge(dim_cohort[["cohort_key", "cohort_id"]], on="cohort_id", how="left")
    fact = fact.merge(dim_snapshot[["snapshot_key", "snapshot_id"]], on="snapshot_id", how="left")
    fact = fact.merge(dim_artist[["artist_key", "primary_artist"]], on="primary_artist", how="left")
    if fact["snapshot_key"].isna().any() or fact["artist_key"].isna().any() or fact["cohort_key"].isna().any():
        raise RuntimeError("Star schema is missing a cohort, snapshot, or artist key")
    fact_track = fact[
        [
            "track_key",
            "snapshot_key",
            "cohort_key",
            "artist_key",
            "raw_band_key",
            "corrected_band_key",
            "chart_position",
            "chart_market",
            "deezer_bpm",
            "popularity",
            "popularity_rank",
            "is_top100",
            "tempo_raw",
            "tempo_corrected",
            "tempo_corrected_alt",
            "octave_shifts",
            "octave_direction",
            "octave_shifted",
            "danceability",
            "energy",
            "valence",
            "speechiness",
            "acousticness",
            "loudness",
            "time_signature",
        ]
    ].copy()

    tables = {
        "dim_cohort": dim_cohort,
        "dim_snapshot": dim_snapshot,
        "dim_artist": dim_artist,
        "dim_track": dim_track,
        "dim_tempo_band": dim_tempo_band,
        "fact_track": fact_track,
    }
    for name, frame in tables.items():
        _write(frame, out_dir / f"{name}.csv")
    return tables


def _write(frame: pd.DataFrame, path: Path) -> None:
    out = frame.copy()
    int_cols = [
        col
        for col in out.columns
        if col.endswith("_key")
        or col
        in {
            "popularity",
            "popularity_rank",
            "is_top100",
            "chart_position",
            "explicit",
            "octave_shifts",
            "octave_shifted",
            "time_signature",
            "duration_ms",
            "sort_order",
        }
    ]
    for col in int_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    out.to_csv(path, index=False, lineterminator="\n")
