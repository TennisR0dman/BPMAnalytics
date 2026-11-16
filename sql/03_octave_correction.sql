-- Half-time and double-time correction.
-- tempo_corrected is the pipeline fold into [70, 140).
-- tempo_folded_sql recomputes that fold in SQL so the rule is visible here:
--   140-279.999 is halved once, 280-559.999 is halved twice,
--   35-69.999 is doubled once, 17.5-34.999 is doubled twice.
-- A track is halved when the corrected tempo is lower than the raw estimate
-- (the estimator was likely counting double-time), and doubled when it is higher.

SELECT
    cohort_id,
    CASE
        WHEN tempo_corrected < tempo_raw - 0.001 THEN 'halved'
        WHEN tempo_corrected > tempo_raw + 0.001 THEN 'doubled'
        ELSE 'unshifted'
    END AS octave_direction,
    COUNT(*) AS n_tracks,
    AVG(tempo_raw) AS mean_raw,
    AVG(tempo_corrected) AS mean_corrected,
    AVG(
        CASE
            WHEN tempo_raw >= 560 THEN tempo_raw / 8.0
            WHEN tempo_raw >= 280 THEN tempo_raw / 4.0
            WHEN tempo_raw >= 140 THEN tempo_raw / 2.0
            WHEN tempo_raw < 17.5 THEN tempo_raw * 8.0
            WHEN tempo_raw < 35 THEN tempo_raw * 4.0
            WHEN tempo_raw < 70 THEN tempo_raw * 2.0
            ELSE tempo_raw
        END
    ) AS mean_folded_sql
FROM track_analysis
WHERE is_top100 = 1
GROUP BY
    cohort_id,
    CASE
        WHEN tempo_corrected < tempo_raw - 0.001 THEN 'halved'
        WHEN tempo_corrected > tempo_raw + 0.001 THEN 'doubled'
        ELSE 'unshifted'
    END
ORDER BY cohort_id, octave_direction;
