#!/usr/bin/env python3
"""Download the pinned Spotify tracks file and check its SHA-256.

The file is the CSV published in maharshipandya/spotify-tracks-dataset at
revision 635b034f69257814eff850a5c2b3346fe458134f. The dataset card declares
license: bsd. This script does not call the Spotify Web API.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bpm_analytics.config import DATASET_SHA256, DATASET_URL, DATA_RAW


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str = DATASET_URL, destination: Path = DATA_RAW) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256(destination) == DATASET_SHA256:
        print(f"Already present and hash matches: {destination}")
        return destination

    temporary = destination.with_suffix(destination.suffix + ".partial")
    request = urllib.request.Request(url)
    print(f"Downloading {url}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    actual = sha256(temporary)
    if actual != DATASET_SHA256:
        temporary.unlink()
        raise SystemExit(
            "Downloaded file hash does not match the pinned hash.\n"
            f"Expected {DATASET_SHA256}\n"
            f"Actual   {actual}"
        )
    temporary.replace(destination)
    print(f"Saved {destination}")
    print(f"SHA-256 {actual}")
    return destination


if __name__ == "__main__":
    download()
