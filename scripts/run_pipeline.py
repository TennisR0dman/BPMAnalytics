#!/usr/bin/env python3
"""Build the analysis table, SQLite warehouse, SQL extracts, star schema, and R report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bpm_analytics.config import (
    DATA_PROCESSED,
    DATA_RAW,
    FIGURE_DIR,
    LOOKUP_PATH,
    RESULTS_PATH,
    ROOT,
    SQL_DIR,
    SQL_OUTPUT_DIR,
    STAR_DIR,
    WAREHOUSE_PATH,
)
from bpm_analytics.cohorts import build_analysis, load_lookup, prepare_catalog
from bpm_analytics.star import write_star
from bpm_analytics.tempo import sql_case_fold
from bpm_analytics.warehouse import ANALYSIS_COLUMNS, connect, load_warehouse, run_query_files


def _round_for_storage(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    float_cols = [
        "tempo_raw",
        "tempo_corrected",
        "tempo_corrected_alt",
        "danceability",
        "energy",
        "valence",
        "speechiness",
        "acousticness",
        "loudness",
    ]
    for col in float_cols:
        out[col] = out[col].astype(float).round(6)
    for col in ("popularity", "popularity_rank", "is_top100", "duration_ms", "explicit", "time_signature", "octave_shifts", "octave_shifted", "raw_band_key", "corrected_band_key"):
        out[col] = out[col].astype(int)
    return out


def _check_sql_fold(frame: pd.DataFrame) -> None:
    mismatch = 0
    for raw, corrected in zip(frame["tempo_raw"], frame["tempo_corrected"]):
        if abs(sql_case_fold(raw) - corrected) > 1e-6:
            mismatch += 1
    if mismatch:
        raise SystemExit(f"{mismatch} rows disagree between the SQL CASE fold and tempo_corrected")


def _check_against_sql(summary: pd.DataFrame, results: dict) -> None:
    for _, row in summary.iterrows():
        cohort = row["cohort_id"]
        published = results["cohorts"][cohort]
        pairs = (
            ("median_raw", "tempo_raw_median"),
            ("mean_raw", "tempo_raw_mean"),
            ("sd_raw", "tempo_raw_sd"),
            ("median_corrected", "tempo_corrected_median"),
            ("mean_corrected", "tempo_corrected_mean"),
        )
        for sql_name, r_name in pairs:
            gap = abs(float(row[sql_name]) - float(published[r_name]))
            if gap > 1e-4:
                raise SystemExit(
                    f"{cohort} {sql_name} disagrees with the R result "
                    f"({row[sql_name]} vs {published[r_name]})"
                )


def main() -> None:
    if not DATA_RAW.exists():
        raise SystemExit("Raw file missing. Run: python scripts/download_data.py")

    raw = pd.read_csv(DATA_RAW)
    catalog = prepare_catalog(raw)
    lookup = load_lookup(LOOKUP_PATH)
    analysis, funnel = build_analysis(catalog, lookup)
    _check_sql_fold(analysis)
    analysis = _round_for_storage(analysis)

    DATA_PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    analysis.loc[:, ANALYSIS_COLUMNS].to_csv(DATA_PROCESSED, index=False, lineterminator="\n")
    funnel_path = ROOT / "outputs" / "funnel.json"
    funnel_path.parent.mkdir(parents=True, exist_ok=True)
    funnel_path.write_text(json.dumps(funnel, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(funnel, indent=2))

    schema = (SQL_DIR / "00_schema.sql").read_text(encoding="utf-8")
    if WAREHOUSE_PATH.exists():
        WAREHOUSE_PATH.unlink()
    conn = connect(WAREHOUSE_PATH)
    try:
        load_warehouse(conn, schema, catalog, lookup, analysis)
        query_results = run_query_files(conn, SQL_DIR, SQL_OUTPUT_DIR)
    finally:
        conn.close()

    write_star(analysis, STAR_DIR)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["Rscript", str(ROOT / "R" / "analysis.R")], cwd=ROOT)
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    _check_against_sql(query_results["01_cohort_summary"], results)
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
