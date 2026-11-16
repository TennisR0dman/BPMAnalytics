-- How the top 100 tracks in each cohort sit across raw tempo bands.
-- Band edges are inclusive on the left and exclusive on the right.
-- 80 BPM is in 80-99, 140 BPM is in 140-159, 160 BPM is in 160 and above.

SELECT
    cohort_id,
    raw_band_key,
    raw_band,
    COUNT(*) AS n_tracks,
    AVG(tempo_raw) AS mean_tempo_raw,
    MIN(tempo_raw) AS min_tempo_raw,
    MAX(tempo_raw) AS max_tempo_raw
FROM track_analysis
WHERE is_top100 = 1
GROUP BY cohort_id, raw_band_key, raw_band
ORDER BY cohort_id, raw_band_key;
