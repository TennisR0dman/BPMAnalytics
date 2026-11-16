"""Cohort rules for the Africa question and the hip-hop comparison.

The source file has no country, no chart position, and no listener market.
`track_genre == afrobeat` is not used as the Africa cohort: the most popular
rows with that label are not African records. See the label-audit query.

Africa cohort
    The text before the first ';' in `artists` is the primary artist.
    That name must match `data/reference/african_primary_artists.csv`.
    A featured artist does not qualify the track. The lookup is a
    project-built list of musicians publicly identified with a national
    popular-music scene in Africa. It is incomplete, and it is not a chart.

US hip-hop cohort
    `track_genre == hip-hop`, and the primary artist is not on the African
    lookup. The genre string is a proxy. The file does not say the track
    charted in the United States, and some rows under this tag are pop or
    non-US records. Those rows stay in, because dropping them would be a
    second, undocumented filter.

Both cohorts
    Drop missing names, non-positive tempo, duration outside 30 seconds to
    20 minutes, and time signatures outside 3-7.
    One row per Spotify track id (highest popularity kept).
    Then one row per primary artist + exact track title, so duplicate
    uploads of the same title do not get two votes.
    Popularity must be at least 40. `is_top100` marks the 100 highest
    popularity rows inside that eligible set. Ties break on track id.
"""

from __future__ import annotations

import pandas as pd

from bpm_analytics.config import (
    AFRICA_COHORT,
    AFROBEAT_GENRE,
    COHORT_NAMES,
    FOLD_HIGH,
    FOLD_HIGH_ALT,
    FOLD_LOW,
    FOLD_LOW_ALT,
    HIPHOP_COHORT,
    HIPHOP_GENRE,
    MAX_DURATION_MS,
    MIN_DURATION_MS,
    MIN_POPULARITY,
    TOP_N,
    VALID_TIME_SIGNATURES,
)
from bpm_analytics.tempo import (
    fold_tempo,
    octave_direction,
    octave_steps,
    tempo_band_key,
    tempo_band_label,
)


def primary_artist(artists) -> str | None:
    """Artist billed first. Spotify separates credits with a semicolon."""
    if artists is None or (isinstance(artists, float) and pd.isna(artists)):
        return None
    text = str(artists).strip()
    if not text or text.lower() == "nan":
        return None
    first = text.split(";", 1)[0].strip()
    return first or None


def load_lookup(path) -> pd.DataFrame:
    lookup = pd.read_csv(path)
    required = {"artist_name", "country", "region", "scene"}
    missing = required - set(lookup.columns)
    if missing:
        raise ValueError(f"Artist lookup is missing columns: {sorted(missing)}")
    lookup = lookup.copy()
    lookup["artist_name"] = lookup["artist_name"].astype(str).str.strip()
    lookup["name_key"] = lookup["artist_name"].str.casefold()
    if lookup["name_key"].duplicated().any():
        dupes = lookup.loc[lookup["name_key"].duplicated(), "artist_name"].tolist()
        raise ValueError(f"Duplicate artist keys in lookup: {dupes}")
    if (lookup["artist_name"] == "").any():
        raise ValueError("Artist lookup contains a blank name")
    return lookup


def prepare_catalog(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize types and add the primary-artist field. Does not filter."""
    frame = raw.copy()
    rename = {}
    if "Unnamed: 0" in frame.columns:
        frame = frame.drop(columns=["Unnamed: 0"])
    frame = frame.rename(columns=rename)
    required = [
        "track_id",
        "artists",
        "album_name",
        "track_name",
        "popularity",
        "duration_ms",
        "explicit",
        "danceability",
        "energy",
        "loudness",
        "speechiness",
        "acousticness",
        "valence",
        "tempo",
        "time_signature",
        "track_genre",
    ]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"Catalog is missing columns: {missing}")

    frame["track_id"] = frame["track_id"].astype(str).str.strip()
    frame = frame[frame["track_id"].ne("") & frame["track_id"].ne("nan")]
    frame["primary_artist"] = frame["artists"].map(primary_artist)
    frame["name_key"] = frame["primary_artist"].fillna("").str.casefold()
    frame["title_key"] = frame["track_name"].fillna("").map(_title_key)
    frame["popularity"] = pd.to_numeric(frame["popularity"], errors="coerce")
    frame["duration_ms"] = pd.to_numeric(frame["duration_ms"], errors="coerce")
    frame["tempo"] = pd.to_numeric(frame["tempo"], errors="coerce")
    frame["time_signature"] = pd.to_numeric(frame["time_signature"], errors="coerce")
    frame["explicit"] = frame["explicit"].map(_as_int_flag)
    for col in ("danceability", "energy", "valence", "speechiness", "acousticness", "loudness"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    text_cols = ("track_name", "artists", "album_name", "track_genre", "primary_artist")
    for col in text_cols:
        frame[col] = frame[col].fillna("").astype(str).str.strip()
    return frame.reset_index(drop=True)


def _title_key(title) -> str:
    if title is None or (isinstance(title, float) and pd.isna(title)):
        return ""
    return " ".join(str(title).strip().casefold().split())


def _as_int_flag(value) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "t", "yes"} else 0
    return 1 if bool(value) else 0


def _quality_mask(frame: pd.DataFrame) -> pd.Series:
    tempo_ok = frame["tempo"].notna() & (frame["tempo"] > 0)
    duration_ok = frame["duration_ms"].between(MIN_DURATION_MS, MAX_DURATION_MS, inclusive="both")
    meter_ok = frame["time_signature"].isin(VALID_TIME_SIGNATURES)
    title_ok = frame["title_key"].ne("")
    artist_ok = frame["name_key"].ne("")
    popularity_ok = frame["popularity"].notna()
    return tempo_ok & duration_ok & meter_ok & title_ok & artist_ok & popularity_ok


def _dedupe(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(
        ["popularity", "track_id"], ascending=[False, True], kind="mergesort"
    )
    by_id = ordered.drop_duplicates("track_id", keep="first")
    by_title = by_id.drop_duplicates(["name_key", "title_key"], keep="first")
    return by_title


def _with_tempo_fields(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["tempo_raw"] = out["tempo"].astype(float)
    out["tempo_corrected"] = out["tempo_raw"].map(lambda v: fold_tempo(v, FOLD_LOW, FOLD_HIGH))
    out["tempo_corrected_alt"] = out["tempo_raw"].map(
        lambda v: fold_tempo(v, FOLD_LOW_ALT, FOLD_HIGH_ALT)
    )
    out["octave_shifts"] = [
        octave_steps(raw, corrected)
        for raw, corrected in zip(out["tempo_raw"], out["tempo_corrected"])
    ]
    out["octave_direction"] = [
        octave_direction(raw, corrected)
        for raw, corrected in zip(out["tempo_raw"], out["tempo_corrected"])
    ]
    out["octave_shifted"] = (out["octave_direction"] != "unshifted").astype(int)
    out["raw_band_key"] = out["tempo_raw"].map(tempo_band_key).astype(int)
    out["raw_band"] = out["raw_band_key"].map(tempo_band_label)
    out["corrected_band_key"] = out["tempo_corrected"].map(tempo_band_key).astype(int)
    out["corrected_band"] = out["corrected_band_key"].map(tempo_band_label)
    return out


def _rank_top(frame: pd.DataFrame, cohort_id: str, top_n: int) -> pd.DataFrame:
    ordered = frame.sort_values(
        ["popularity", "track_id"], ascending=[False, True], kind="mergesort"
    ).copy()
    ordered["popularity_rank"] = range(1, len(ordered) + 1)
    ordered["is_top100"] = (ordered["popularity_rank"] <= top_n).astype(int)
    ordered["cohort_id"] = cohort_id
    ordered["cohort_name"] = COHORT_NAMES[cohort_id]
    return ordered


def build_analysis(
    catalog: pd.DataFrame,
    lookup: pd.DataFrame,
    top_n: int = TOP_N,
    min_popularity: int = MIN_POPULARITY,
) -> tuple[pd.DataFrame, dict]:
    """Return the eligible analysis table and a row-count funnel."""
    lookup_keys = set(lookup["name_key"])
    funnel = {"catalog_rows": int(len(catalog))}

    africa_rows = catalog[catalog["name_key"].isin(lookup_keys)].copy()
    funnel["africa_rows_primary_match"] = int(len(africa_rows))
    africa_ids = set(africa_rows["track_id"])
    africa_rows = africa_rows[_quality_mask(africa_rows)]
    funnel["africa_rows_after_quality"] = int(len(africa_rows))
    africa_rows = _dedupe(africa_rows)
    funnel["africa_tracks_after_dedupe"] = int(len(africa_rows))
    africa_rows = africa_rows[africa_rows["popularity"] >= min_popularity]
    funnel["africa_eligible"] = int(len(africa_rows))
    africa = _rank_top(_with_tempo_fields(africa_rows), AFRICA_COHORT, top_n)
    africa = africa.merge(
        lookup[["name_key", "country", "region", "scene", "artist_name"]],
        on="name_key",
        how="left",
        validate="many_to_one",
    )
    # Keep the catalog's spelling in primary_artist; country comes from the lookup.
    africa = africa.drop(columns=["artist_name"])

    hip_rows = catalog[catalog["track_genre"].eq(HIPHOP_GENRE)].copy()
    funnel["hiphop_genre_rows"] = int(len(hip_rows))
    hip_rows = hip_rows[~hip_rows["name_key"].isin(lookup_keys)]
    hip_rows = hip_rows[~hip_rows["track_id"].isin(africa_ids)]
    funnel["hiphop_rows_after_africa_exclusion"] = int(len(hip_rows))
    hip_rows = hip_rows[_quality_mask(hip_rows)]
    funnel["hiphop_rows_after_quality"] = int(len(hip_rows))
    hip_rows = _dedupe(hip_rows)
    funnel["hiphop_tracks_after_dedupe"] = int(len(hip_rows))
    hip_rows = hip_rows[hip_rows["popularity"] >= min_popularity]
    funnel["hiphop_eligible"] = int(len(hip_rows))
    hip = _rank_top(_with_tempo_fields(hip_rows), HIPHOP_COHORT, top_n)
    hip["country"] = pd.NA
    hip["region"] = pd.NA
    hip["scene"] = pd.NA

    analysis = pd.concat([africa, hip], ignore_index=True)
    shared = set(africa["track_id"]) & set(hip["track_id"])
    if shared:
        raise RuntimeError(f"Track ids landed in both cohorts: {sorted(shared)[:5]}")
    funnel["analysis_rows"] = int(len(analysis))
    funnel["top_n"] = int(top_n)
    funnel["min_popularity"] = int(min_popularity)
    return analysis, funnel


def afrobeat_label_audit(catalog: pd.DataFrame, lookup: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    """Highest-popularity rows labeled afrobeat, with a lookup flag.

    `on_african_lookup` is 1 only when the primary artist is on this project's
    list. A 0 does not prove the artist is non-African; the list is incomplete.
    The head of the genre is still the right place to see that the label is
    not a list of top African songs.
    """
    labeled = catalog[catalog["track_genre"].eq(AFROBEAT_GENRE)].copy()
    labeled = labeled.sort_values(
        ["popularity", "track_id"], ascending=[False, True], kind="mergesort"
    )
    labeled = labeled.drop_duplicates("track_id", keep="first").head(limit)
    keys = set(lookup["name_key"])
    labeled["on_african_lookup"] = labeled["name_key"].isin(keys).astype(int)
    columns = [
        "track_id",
        "track_name",
        "artists",
        "primary_artist",
        "popularity",
        "tempo",
        "track_genre",
        "on_african_lookup",
    ]
    out = labeled[columns].rename(columns={"tempo": "tempo_raw"})
    return out.reset_index(drop=True)
