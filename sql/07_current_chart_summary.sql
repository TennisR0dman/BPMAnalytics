-- Current-chart tempos measured from Deezer previews.
-- tempo_raw is the librosa beat estimate. deezer_bpm is the service field
-- and is often zero, so averages of that column are not the headline.

SELECT
    cohort_id,
    COUNT(*) AS n_tracks,
    AVG(tempo_raw) AS mean_librosa_bpm,
    AVG(tempo_corrected) AS mean_corrected,
    AVG(CASE WHEN deezer_bpm > 0 THEN deezer_bpm END) AS mean_deezer_bpm_when_set,
    SUM(CASE WHEN deezer_bpm > 0 THEN 1 ELSE 0 END) AS n_deezer_bpm
FROM chart_analysis
GROUP BY cohort_id
ORDER BY cohort_id;
