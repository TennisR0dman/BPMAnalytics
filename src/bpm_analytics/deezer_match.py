"""Choose a Deezer track for a chart row.

The search itself is network I/O and stays in the build script. This module
only scores candidates the caller already has, so tests do not call Deezer.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher


_PARENS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_FEAT = re.compile(r"\b(feat\.?|ft\.?|featuring|with)\b.*", re.I)


def normalize_text(value: str) -> str:
    text = "" if value is None else str(value)
    text = text.casefold().replace("&", " and ")
    text = _PARENS.sub(" ", text)
    text = _FEAT.sub(" ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def score_candidate(artist: str, title: str, candidate: dict) -> dict:
    """Score one Deezer search hit against the chart artist and title."""
    query_artist = normalize_text(artist)
    query_title = normalize_text(title)
    cand_artist = normalize_text((candidate.get("artist") or {}).get("name", ""))
    cand_title = normalize_text(candidate.get("title_short") or candidate.get("title") or "")
    title_ratio = _ratio(query_title, cand_title)
    artist_ratio = _ratio(query_artist, cand_artist)
    contained = bool(query_artist) and (
        query_artist in cand_artist or cand_artist in query_artist
    )
    if contained:
        artist_ratio = max(artist_ratio, 0.85 if len(query_artist) >= 3 else artist_ratio)
    return {
        "deezer_id": candidate.get("id"),
        "deezer_title": candidate.get("title") or "",
        "deezer_artist": (candidate.get("artist") or {}).get("name", ""),
        "title_ratio": round(title_ratio, 4),
        "artist_ratio": round(artist_ratio, 4),
        "preview": candidate.get("preview") or "",
    }


def pick_match(artist: str, title: str, candidates: list[dict]) -> dict | None:
    """Return the best acceptable hit, or None.

    A match needs a close title. The artist can be a little looser when one
    name contains the other, because chart credits and Deezer credits often
    differ by a featured artist.
    """
    best = None
    best_key = (-1.0, -1.0)
    for candidate in candidates:
        scored = score_candidate(artist, title, candidate)
        title_ratio = scored["title_ratio"]
        artist_ratio = scored["artist_ratio"]
        acceptable = title_ratio >= 0.82 and artist_ratio >= 0.55
        if not acceptable:
            continue
        key = (title_ratio, artist_ratio)
        if key > best_key:
            best = scored
            best_key = key
    return best
