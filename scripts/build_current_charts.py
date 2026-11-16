#!/usr/bin/env python3
"""Fetch current chart snapshots, match Deezer previews, and estimate BPM.

Audio files stay in data/cache/previews and are not part of the repo.
Re-running uses the saved chart CSVs and any previews already on disk.
Pass --refresh-charts to download the chart pages again.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bpm_analytics.bpm_audio import estimate_bpm
from bpm_analytics.charts import parse_billboard_rb_hiphop, parse_kworb_daily
from bpm_analytics.config import FOLD_HIGH, FOLD_HIGH_ALT, FOLD_LOW, FOLD_LOW_ALT, ROOT
from bpm_analytics.deezer_match import normalize_text, pick_match
from bpm_analytics.tempo import fold_tempo, octave_direction, octave_steps, tempo_band_key, tempo_band_label

FETCH_DATE = "2026-11-16"
CURRENT_DIR = ROOT / "data" / "current"
PREVIEW_DIR = ROOT / "data" / "cache" / "previews"
PAUSE_SECONDS = 0.35

CHARTS = [
    {
        "kind": "kworb",
        "market": "Nigeria",
        "url": "https://kworb.net/spotify/country/ng_daily.html",
        "csv_name": "nigeria_spotify_daily.csv",
        "cohort_id": "africa_charts",
        "comparison_arm": "africa",
    },
    {
        "kind": "kworb",
        "market": "South Africa",
        "url": "https://kworb.net/spotify/country/za_daily.html",
        "csv_name": "south_africa_spotify_daily.csv",
        "cohort_id": "africa_charts",
        "comparison_arm": "africa",
    },
    {
        "kind": "billboard",
        "market": "United States",
        "url": "https://www.billboard.com/charts/r-b-hip-hop-songs/",
        "csv_name": "us_billboard_rb_hiphop.csv",
        "cohort_id": "us_rb_hiphop_chart",
        "comparison_arm": "hiphop",
    },
]


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"Accept": "text/html,application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_chart_pages(refresh: bool) -> pd.DataFrame:
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for spec in CHARTS:
        destination = CURRENT_DIR / spec["csv_name"]
        if destination.exists() and not refresh:
            frame = pd.read_csv(destination)
            print(f"Using saved {destination.name} ({len(frame)} rows)")
            frames.append(frame)
            continue
        print(f"Fetching {spec['url']}")
        html = _get(spec["url"])
        if spec["kind"] == "kworb":
            rows = parse_kworb_daily(html, spec["market"], spec["url"], FETCH_DATE, top_n=50)
        else:
            rows = parse_billboard_rb_hiphop(html, spec["url"], FETCH_DATE)
        frame = pd.DataFrame(rows)
        frame["cohort_id"] = spec["cohort_id"]
        frame["comparison_arm"] = spec["comparison_arm"]
        frame.to_csv(destination, index=False)
        print(f"Wrote {destination.name} ({len(frame)} rows, chart date {frame['chart_date'].iloc[0]})")
        frames.append(frame)
        time.sleep(PAUSE_SECONDS)
    return pd.concat(frames, ignore_index=True)


def _dedupe_charts(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per Spotify id inside a cohort. Billboard rows have no Spotify id."""
    pieces = []
    for cohort_id, group in frame.groupby("cohort_id", sort=False):
        with_id = group[group["spotify_track_id"].fillna("").astype(str).str.len() > 0].copy()
        without_id = group[group["spotify_track_id"].fillna("").astype(str).str.len() == 0].copy()
        if not with_id.empty:
            with_id = with_id.sort_values(["chart_position", "chart_market"], kind="mergesort")
            collapsed = []
            for _track_id, rows in with_id.groupby("spotify_track_id", sort=False):
                rows = rows.sort_values("chart_position", kind="mergesort")
                kept = rows.iloc[0].copy()
                markets = sorted(set(rows["chart_market"]))
                kept["chart_market"] = "; ".join(markets)
                kept["chart_position"] = int(rows["chart_position"].min())
                collapsed.append(kept)
            with_id = pd.DataFrame(collapsed)
        pieces.append(pd.concat([with_id, without_id], ignore_index=True))
    combined = pd.concat(pieces, ignore_index=True)
    combined.insert(0, "chart_row_id", [f"c{i:04d}" for i in range(1, len(combined) + 1)])
    return combined.sort_values(["cohort_id", "chart_position", "chart_row_id"], kind="mergesort")


def _search(artist: str, title: str) -> list[dict]:
    title_core = normalize_text(title)
    queries = [
        f'artist:"{artist}" track:"{title_core}"',
        f"{artist} {title_core}",
    ]
    for query in queries:
        url = "https://api.deezer.com/search?" + urllib.parse.urlencode({"q": query, "limit": "10"})
        try:
            payload = _get_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(5)
                payload = _get_json(url)
            else:
                raise
        hits = payload.get("data") or []
        time.sleep(PAUSE_SECONDS)
        if hits:
            return hits
    return []


def match_deezer(charts: pd.DataFrame, refresh: bool) -> pd.DataFrame:
    destination = CURRENT_DIR / "deezer_matches.csv"
    if destination.exists() and not refresh:
        print(f"Using saved {destination.name}")
        return pd.read_csv(destination)
    rows = []
    for record in charts.itertuples(index=False):
        hits = _search(record.primary_artist, record.track_name)
        chosen = pick_match(record.primary_artist, record.track_name, hits)
        reason = "matched" if chosen else "no_deezer_match"
        deezer_bpm = None
        preview = ""
        deezer_id = None
        deezer_title = ""
        deezer_artist = ""
        title_ratio = None
        artist_ratio = None
        if chosen:
            deezer_id = int(chosen["deezer_id"])
            detail = _get_json(f"https://api.deezer.com/track/{deezer_id}")
            time.sleep(PAUSE_SECONDS)
            preview = detail.get("preview") or chosen.get("preview") or ""
            deezer_bpm = detail.get("bpm")
            deezer_title = detail.get("title") or chosen["deezer_title"]
            deezer_artist = (detail.get("artist") or {}).get("name") or chosen["deezer_artist"]
            title_ratio = chosen["title_ratio"]
            artist_ratio = chosen["artist_ratio"]
            if not preview:
                reason = "no_preview"
        rows.append(
            {
                "chart_row_id": record.chart_row_id,
                "cohort_id": record.cohort_id,
                "comparison_arm": record.comparison_arm,
                "chart_market": record.chart_market,
                "chart_position": record.chart_position,
                "chart_date": record.chart_date,
                "fetch_date": record.fetch_date,
                "source_url": record.source_url,
                "source_name": record.source_name,
                "primary_artist": record.primary_artist,
                "track_name": record.track_name,
                "spotify_track_id": record.spotify_track_id,
                "match_status": reason,
                "deezer_id": deezer_id,
                "deezer_title": deezer_title,
                "deezer_artist": deezer_artist,
                "title_ratio": title_ratio,
                "artist_ratio": artist_ratio,
                "deezer_bpm": deezer_bpm,
                "preview_url": preview,
            }
        )
        print(f"{record.chart_row_id} {record.primary_artist} - {record.track_name}: {reason}")
    frame = pd.DataFrame(rows)
    frame.to_csv(destination, index=False)
    return frame


def _download_preview(deezer_id: int, url: str) -> Path | None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    destination = PREVIEW_DIR / f"{deezer_id}.mp3"
    if destination.exists() and destination.stat().st_size > 1000:
        return destination
    try:
        request = urllib.request.Request(url, headers={"Accept": "audio/mpeg"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.URLError:
        return None
    if len(payload) < 1000:
        return None
    destination.write_bytes(payload)
    return destination


def estimate_all(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for record in matches.itertuples(index=False):
        librosa_bpm = None
        librosa_tempo_bpm = None
        method = ""
        status = record.match_status
        if record.match_status == "matched" and isinstance(record.preview_url, str) and record.preview_url:
            path = _download_preview(int(record.deezer_id), record.preview_url)
            if path is None:
                status = "no_preview"
            else:
                try:
                    estimated = estimate_bpm(str(path))
                except Exception as exc:  # audio decode failures stay in the log
                    estimated = {"librosa_bpm": None, "librosa_tempo_bpm": None, "librosa_method": "failed"}
                    print(f"bpm failed {record.deezer_id}: {exc}")
                librosa_bpm = estimated["librosa_bpm"]
                librosa_tempo_bpm = estimated["librosa_tempo_bpm"]
                method = estimated["librosa_method"]
                status = "measured" if librosa_bpm else "bpm_failed"
        elif record.match_status == "matched":
            status = "no_preview"
        rows.append({**record._asdict(), "measure_status": status, "librosa_bpm": librosa_bpm, "librosa_tempo_bpm": librosa_tempo_bpm, "librosa_method": method})
        print(f"measure {record.chart_row_id} {status} {librosa_bpm}")
    frame = pd.DataFrame(rows)
    frame.to_csv(CURRENT_DIR / "measurement_log.csv", index=False)
    return frame


def _analysis_frame(measured: pd.DataFrame) -> pd.DataFrame:
    kept = measured[measured["measure_status"] == "measured"].copy()
    kept["tempo_raw"] = kept["librosa_bpm"].astype(float)
    kept["tempo_corrected"] = kept["tempo_raw"].map(lambda value: fold_tempo(value, FOLD_LOW, FOLD_HIGH))
    kept["tempo_corrected_alt"] = kept["tempo_raw"].map(lambda value: fold_tempo(value, FOLD_LOW_ALT, FOLD_HIGH_ALT))
    kept["octave_shifts"] = [octave_steps(raw, corrected) for raw, corrected in zip(kept["tempo_raw"], kept["tempo_corrected"])]
    kept["octave_direction"] = [octave_direction(raw, corrected) for raw, corrected in zip(kept["tempo_raw"], kept["tempo_corrected"])]
    kept["octave_shifted"] = (kept["octave_direction"] != "unshifted").astype(int)
    kept["raw_band_key"] = kept["tempo_raw"].map(tempo_band_key).astype(int)
    kept["raw_band"] = kept["raw_band_key"].map(tempo_band_label)
    kept["corrected_band_key"] = kept["tempo_corrected"].map(tempo_band_key).astype(int)
    kept["corrected_band"] = kept["corrected_band_key"].map(tempo_band_label)
    kept["snapshot_id"] = "current_charts"
    kept["track_id"] = kept["deezer_id"].map(lambda value: f"deezer:{int(value)}")
    kept["artists"] = kept["primary_artist"]
    kept["album_name"] = ""
    kept["is_top100"] = 1
    names = {
        "africa_charts": "Nigeria and South Africa Spotify charts",
        "us_rb_hiphop_chart": "Billboard Hot R&B/Hip-Hop Songs",
    }
    kept["cohort_name"] = kept["cohort_id"].map(names)
    columns = [
        "snapshot_id",
        "cohort_id",
        "cohort_name",
        "comparison_arm",
        "track_id",
        "track_name",
        "artists",
        "album_name",
        "primary_artist",
        "chart_market",
        "chart_position",
        "chart_date",
        "fetch_date",
        "source_url",
        "source_name",
        "spotify_track_id",
        "deezer_id",
        "deezer_title",
        "deezer_artist",
        "deezer_bpm",
        "title_ratio",
        "artist_ratio",
        "librosa_bpm",
        "librosa_tempo_bpm",
        "librosa_method",
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
        "is_top100",
    ]
    return kept[columns].sort_values(["cohort_id", "chart_position", "track_id"], kind="mergesort")


def write_coverage(charts: pd.DataFrame, measured: pd.DataFrame) -> dict:
    summary = {"fetch_date": FETCH_DATE, "cohorts": {}}
    for cohort_id, group in charts.groupby("cohort_id"):
        subset = measured[measured["cohort_id"] == cohort_id]
        chart_rows = int(len(group))
        matched = int((subset["match_status"] != "no_deezer_match").sum())
        measured_n = int((subset["measure_status"] == "measured").sum())
        no_preview = int(subset["measure_status"].isin(["no_preview"]).sum())
        deezer_bpm = pd.to_numeric(subset["deezer_bpm"], errors="coerce")
        summary["cohorts"][cohort_id] = {
            "chart_rows": chart_rows,
            "deezer_matched": matched,
            "no_preview": no_preview,
            "librosa_measured": measured_n,
            "coverage_rate": round(measured_n / chart_rows, 4) if chart_rows else 0,
            "deezer_bpm_nonzero": int((deezer_bpm.fillna(0) > 0).sum()),
        }
    path = CURRENT_DIR / "coverage.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    refresh = "--refresh-charts" in sys.argv
    refresh_match = "--refresh-matches" in sys.argv or refresh
    raw = fetch_chart_pages(refresh)
    charts = _dedupe_charts(raw)
    charts.to_csv(CURRENT_DIR / "chart_rows.csv", index=False)
    matches = match_deezer(charts, refresh_match)
    measured = estimate_all(matches)
    analysis = _analysis_frame(measured)
    analysis.to_csv(CURRENT_DIR / "chart_analysis.csv", index=False)
    write_coverage(charts, measured)
    print(f"Analysis rows {len(analysis)}")


if __name__ == "__main__":
    main()
