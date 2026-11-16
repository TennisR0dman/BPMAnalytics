"""Power BI star-schema extracts.

Grain of fact_track: one eligible track in one cohort.
Tempo band is a role-playing dimension: raw_band_key is the active
relationship, corrected_band_key is the second role.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bpm_analytics.config import AFRICA_COHORT, BANDS, COHORT_NAMES, HIPHOP_COHORT


COHORT_DEFINITIONS = {
    AFRICA_COHORT: (
        "Primary artist is on the African-scene lookup. Popularity is at least 40. "
        "is_top100 marks the 100 highest-popularity tracks. Not a country chart."
    ),
    HIPHOP_COHORT: (
        "track_genre is hip-hop and the primary artist is not on the African-scene lookup. "
        "Popularity is at least 40. Genre proxy only: the file has no US chart flag."
    ),
}


def write_star(analysis: pd.DataFrame, out_dir: Path) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dim_cohort = pd.DataFrame(
        [
            {
                "cohort_key": 1,
                "cohort_id": AFRICA_COHORT,
                "cohort_name": COHORT_NAMES[AFRICA_COHORT],
                "definition": COHORT_DEFINITIONS[AFRICA_COHORT],
            },
            {
                "cohort_key": 2,
                "cohort_id": HIPHOP_COHORT,
                "cohort_name": COHORT_NAMES[HIPHOP_COHORT],
                "definition": COHORT_DEFINITIONS[HIPHOP_COHORT],
            },
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
        analysis[["primary_artist", "country", "region", "scene", "cohort_id"]]
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

    tracks = analysis.sort_values(["cohort_id", "track_id"], kind="mergesort").copy()
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
    fact = fact.merge(dim_artist[["artist_key", "primary_artist"]], on="primary_artist", how="left")
    fact_track = fact[
        [
            "track_key",
            "cohort_key",
            "artist_key",
            "raw_band_key",
            "corrected_band_key",
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
