"""Paths, cohort rules, and the pinned public data source."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = ROOT / "data" / "raw" / "dataset.csv"
DATA_PROCESSED = ROOT / "data" / "processed" / "analysis_tracks.csv"
LOOKUP_PATH = ROOT / "data" / "reference" / "african_primary_artists.csv"
SQL_DIR = ROOT / "sql"
WAREHOUSE_PATH = ROOT / "data" / "warehouse" / "tracks.sqlite"
SQL_OUTPUT_DIR = ROOT / "outputs" / "sql"
STAR_DIR = ROOT / "powerbi" / "star"
RESULTS_PATH = ROOT / "outputs" / "results.json"
FIGURE_DIR = ROOT / "outputs" / "figures"

DATASET_REPO = "maharshipandya/spotify-tracks-dataset"
DATASET_REVISION = "635b034f69257814eff850a5c2b3346fe458134f"
DATASET_SHA256 = "b202fa49909b2d5cef71a04b1d21243cfeb36414535f2ca9272aa646721177bd"
DATASET_URL = (
    "https://huggingface.co/datasets/"
    f"{DATASET_REPO}/resolve/{DATASET_REVISION}/dataset.csv"
)
DATASET_LICENSE = "bsd"

# Headline comparison: 100 highest-popularity tracks in each cohort.
TOP_N = 100
# Floor applied before ranking, so catalog filler at popularity 0 is not eligible.
MIN_POPULARITY = 40
MIN_DURATION_MS = 30_000
MAX_DURATION_MS = 1_200_000
VALID_TIME_SIGNATURES = (3, 4, 5, 6, 7)

# Primary octave window. Values outside [low, high) are halved or doubled
# until they fall inside, which is the usual half-time / double-time fix.
FOLD_LOW = 70.0
FOLD_HIGH = 140.0
# Second window, reported as a sensitivity check only.
FOLD_LOW_ALT = 80.0
FOLD_HIGH_ALT = 160.0

AFRICA_COHORT = "africa_popular"
HIPHOP_COHORT = "us_hiphop_genre"
COHORT_NAMES = {
    AFRICA_COHORT: "African popular music",
    HIPHOP_COHORT: "US hip-hop (genre proxy)",
}
HIPHOP_GENRE = "hip-hop"
AFROBEAT_GENRE = "afrobeat"

BANDS = (
    (1, "Under 80", 0.0, 80.0),
    (2, "80-99", 80.0, 100.0),
    (3, "100-119", 100.0, 120.0),
    (4, "120-139", 120.0, 140.0),
    (5, "140-159", 140.0, 160.0),
    (6, "160 and above", 160.0, None),
)
