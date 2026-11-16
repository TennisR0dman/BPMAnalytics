"""SQLite warehouse and the sql/ analysis queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

CATALOG_COLUMNS = [
    "track_id",
    "track_name",
    "artists",
    "album_name",
    "primary_artist",
    "popularity",
    "duration_ms",
    "explicit",
    "tempo",
    "time_signature",
    "track_genre",
    "danceability",
    "energy",
    "valence",
    "speechiness",
    "acousticness",
    "loudness",
]

ANALYSIS_COLUMNS = [
    "cohort_id",
    "cohort_name",
    "track_id",
    "track_name",
    "artists",
    "album_name",
    "primary_artist",
    "country",
    "region",
    "scene",
    "track_genre",
    "popularity",
    "popularity_rank",
    "is_top100",
    "duration_ms",
    "explicit",
    "tempo_raw",
    "tempo_corrected",
    "tempo_corrected_alt",
    "octave_shifts",
    "octave_direction",
    "octave_shifted",
    "raw_band_key",
    "raw_band",
    "corrected_band_key",
    "corrected_band",
    "danceability",
    "energy",
    "valence",
    "speechiness",
    "acousticness",
    "loudness",
    "time_signature",
]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _as_sql_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            return value
    return value


def _frame_for_sql(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.loc[:, columns].copy()
    return out.astype(object).where(pd.notna(out), None)


def load_warehouse(
    conn: sqlite3.Connection,
    schema_sql: str,
    catalog: pd.DataFrame,
    lookup: pd.DataFrame,
    analysis: pd.DataFrame,
) -> None:
    conn.executescript(schema_sql)
    _insert(conn, "artist_lookup", lookup[["artist_name", "country", "region", "scene"]])
    _insert(conn, "tracks_catalog", _frame_for_sql(catalog, CATALOG_COLUMNS))
    _insert(conn, "track_analysis", _frame_for_sql(analysis, ANALYSIS_COLUMNS))
    conn.commit()


def _insert(conn: sqlite3.Connection, table: str, frame: pd.DataFrame) -> None:
    columns = list(frame.columns)
    placeholders = ", ".join(["?"] * len(columns))
    quoted = ", ".join(columns)
    sql = f"INSERT INTO {table} ({quoted}) VALUES ({placeholders})"
    rows = [tuple(_as_sql_value(value) for value in record) for record in frame.itertuples(index=False, name=None)]
    conn.executemany(sql, rows)


def run_query_files(conn: sqlite3.Connection, sql_dir: Path, out_dir: Path) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for path in sorted(sql_dir.glob("[0-9][0-9]_*.sql")):
        if path.name.startswith("00_"):
            continue
        query = path.read_text(encoding="utf-8")
        frame = pd.read_sql_query(query, conn)
        frame.to_csv(out_dir / f"{path.stem}.csv", index=False)
        results[path.stem] = frame
    return results
