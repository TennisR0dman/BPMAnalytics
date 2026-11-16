-- Spotify popularity (0-100 index) by raw tempo band, headline tracks only.
-- Popularity is an index, so the query averages it. It does not sum it.

SELECT
    cohort_id,
    raw_band_key,
    raw_band,
    COUNT(*) AS n_tracks,
    AVG(popularity) AS mean_popularity,
    MIN(popularity) AS min_popularity,
    MAX(popularity) AS max_popularity,
    AVG(tempo_raw) AS mean_tempo_raw,
    AVG(danceability) AS mean_danceability,
    AVG(energy) AS mean_energy
FROM track_analysis
WHERE is_top100 = 1
GROUP BY cohort_id, raw_band_key, raw_band
ORDER BY cohort_id, raw_band_key;
