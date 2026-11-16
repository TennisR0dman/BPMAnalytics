"""Parsers for the public chart pages used as the current-chart snapshot.

The fetch step saves these rows as CSV. Tests feed HTML strings and do not
touch the network.
"""

from __future__ import annotations

import re
from html import unescape


_KW_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_KW_POS = re.compile(r'<td class="np">(\d+)</td>')
_KW_ARTIST = re.compile(r'href="\.\./artist/[^"]+">([^<]+)</a>')
_KW_TRACK = re.compile(r'href="\.\./track/([^"]+)\.html">([^<]+)</a>')
_KW_DATE = re.compile(r"(\d{4}/\d{2}/\d{2})")
_BB_WEEK = re.compile(r"Week of ([A-Za-z]+ \d{1,2}, \d{4})")
_BB_TITLE = re.compile(r'id="title-of-a-story"[^>]*>\s*(.*?)\s*</h3>', re.S)
_BB_ARTIST = re.compile(r"</h3>\s*<span[^>]*>(.*?)</span>", re.S)


def _clean(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_kworb_daily(html: str, market: str, source_url: str, fetch_date: str, top_n: int = 50) -> list[dict]:
    """Top rows of a kworb Spotify country daily chart.

    The lead artist is the first artist link. The track link text is the title.
    Featured names inside the row are not part of the title.
    """
    date_match = _KW_DATE.search(html)
    if not date_match:
        raise ValueError(f"No chart date in the {market} kworb page")
    chart_date = date_match.group(1).replace("/", "-")
    rows = []
    for chunk in _KW_ROW.findall(html):
        pos_match = _KW_POS.search(chunk)
        artist_match = _KW_ARTIST.search(chunk)
        track_match = _KW_TRACK.search(chunk)
        if not (pos_match and artist_match and track_match):
            continue
        position = int(pos_match.group(1))
        if position > top_n:
            continue
        rows.append(
            {
                "chart_market": market,
                "chart_position": position,
                "primary_artist": _clean(artist_match.group(1)),
                "track_name": _clean(track_match.group(2)),
                "spotify_track_id": track_match.group(1),
                "chart_date": chart_date,
                "fetch_date": fetch_date,
                "source_url": source_url,
                "source_name": f"Kworb Spotify daily chart, {market}",
            }
        )
    if not rows:
        raise ValueError(f"No chart rows parsed for {market}")
    rows.sort(key=lambda row: row["chart_position"])
    return rows


def parse_billboard_rb_hiphop(html: str, source_url: str, fetch_date: str) -> list[dict]:
    """Billboard Hot R&B/Hip-Hop Songs rows from the public chart page."""
    week_match = _BB_WEEK.search(html)
    if not week_match:
        raise ValueError("No Billboard week label in the chart page")
    chart_date = week_match.group(1)
    rows = []
    parts = html.split('data-detail-target="')[1:]
    for part in parts:
        pos_text = part.split('"', 1)[0]
        if not pos_text.isdigit():
            continue
        title_match = _BB_TITLE.search(part)
        artist_match = _BB_ARTIST.search(part)
        if not (title_match and artist_match):
            continue
        artist = _clean(re.sub(r"<[^>]+>", " ", artist_match.group(1)))
        title = _clean(re.sub(r"<[^>]+>", " ", title_match.group(1)))
        if not artist or not title:
            continue
        rows.append(
            {
                "chart_market": "United States",
                "chart_position": int(pos_text),
                "primary_artist": artist,
                "track_name": title,
                "spotify_track_id": "",
                "chart_date": chart_date,
                "fetch_date": fetch_date,
                "source_url": source_url,
                "source_name": "Billboard Hot R&B/Hip-Hop Songs",
            }
        )
    # The page repeats some markup. Keep the first copy of each position.
    kept = {}
    for row in rows:
        kept.setdefault(row["chart_position"], row)
    ordered = [kept[pos] for pos in sorted(kept)]
    if len(ordered) < 10:
        raise ValueError(f"Expected a full Billboard chart, parsed {len(ordered)} rows")
    return ordered
