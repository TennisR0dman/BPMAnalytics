DROP TABLE IF EXISTS chart_analysis;
DROP TABLE IF EXISTS track_analysis;
DROP TABLE IF EXISTS tracks_catalog;
DROP TABLE IF EXISTS artist_lookup;

CREATE TABLE artist_lookup (
    artist_name TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    region TEXT NOT NULL,
    scene TEXT NOT NULL
);

CREATE TABLE tracks_catalog (
    track_id TEXT NOT NULL,
    track_name TEXT,
    artists TEXT,
    album_name TEXT,
    primary_artist TEXT,
    popularity INTEGER,
    duration_ms INTEGER,
    explicit INTEGER,
    tempo REAL,
    time_signature INTEGER,
    track_genre TEXT,
    danceability REAL,
    energy REAL,
    valence REAL,
    speechiness REAL,
    acousticness REAL,
    loudness REAL
);

CREATE TABLE track_analysis (
    cohort_id TEXT NOT NULL,
    cohort_name TEXT NOT NULL,
    track_id TEXT NOT NULL,
    track_name TEXT,
    artists TEXT,
    album_name TEXT,
    primary_artist TEXT NOT NULL,
    country TEXT,
    region TEXT,
    scene TEXT,
    track_genre TEXT,
    popularity INTEGER NOT NULL,
    popularity_rank INTEGER NOT NULL,
    is_top100 INTEGER NOT NULL,
    duration_ms INTEGER,
    explicit INTEGER,
    tempo_raw REAL NOT NULL,
    tempo_corrected REAL NOT NULL,
    tempo_corrected_alt REAL NOT NULL,
    octave_shifts INTEGER NOT NULL,
    octave_direction TEXT NOT NULL,
    octave_shifted INTEGER NOT NULL,
    raw_band_key INTEGER NOT NULL,
    raw_band TEXT NOT NULL,
    corrected_band_key INTEGER NOT NULL,
    corrected_band TEXT NOT NULL,
    danceability REAL,
    energy REAL,
    valence REAL,
    speechiness REAL,
    acousticness REAL,
    loudness REAL,
    time_signature INTEGER,
    PRIMARY KEY (cohort_id, track_id)
);

CREATE TABLE chart_analysis (
    cohort_id TEXT NOT NULL,
    track_id TEXT NOT NULL,
    track_name TEXT,
    primary_artist TEXT,
    chart_market TEXT,
    chart_position INTEGER,
    tempo_raw REAL NOT NULL,
    tempo_corrected REAL NOT NULL,
    tempo_corrected_alt REAL NOT NULL,
    deezer_bpm REAL,
    librosa_bpm REAL,
    is_top100 INTEGER NOT NULL
);

CREATE INDEX idx_analysis_top ON track_analysis (cohort_id, is_top100);
CREATE INDEX idx_catalog_genre ON tracks_catalog (track_genre);
CREATE INDEX idx_catalog_track ON tracks_catalog (track_id);
