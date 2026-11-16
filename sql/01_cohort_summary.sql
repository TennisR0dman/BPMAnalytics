-- Summary of the headline set: the 100 highest-popularity tracks in each cohort.
-- Median is the average of the two central rows when the count is even.
-- Standard deviation is the sample standard deviation (divide by n - 1).

WITH top_tracks AS (
    SELECT
        cohort_id,
        track_id,
        tempo_raw,
        tempo_corrected,
        popularity,
        octave_shifted
    FROM track_analysis
    WHERE is_top100 = 1
),
moments AS (
    SELECT
        cohort_id,
        COUNT(*) AS n_tracks,
        AVG(tempo_raw) AS mean_raw,
        AVG(tempo_corrected) AS mean_corrected,
        MIN(tempo_raw) AS min_raw,
        MAX(tempo_raw) AS max_raw,
        AVG(popularity) AS mean_popularity,
        MIN(popularity) AS min_popularity,
        MAX(popularity) AS max_popularity,
        SUM(octave_shifted) AS n_octave_shifted
    FROM top_tracks
    GROUP BY cohort_id
),
ranked AS (
    SELECT
        cohort_id,
        tempo_raw,
        tempo_corrected,
        ROW_NUMBER() OVER (
            PARTITION BY cohort_id
            ORDER BY tempo_raw, track_id
        ) AS rn_raw,
        ROW_NUMBER() OVER (
            PARTITION BY cohort_id
            ORDER BY tempo_corrected, track_id
        ) AS rn_corrected,
        COUNT(*) OVER (PARTITION BY cohort_id) AS n_tracks
    FROM top_tracks
),
medians AS (
    SELECT
        cohort_id,
        AVG(
            CASE
                WHEN rn_raw IN ((n_tracks + 1) / 2, (n_tracks + 2) / 2)
                THEN tempo_raw
            END
        ) AS median_raw,
        AVG(
            CASE
                WHEN rn_corrected IN ((n_tracks + 1) / 2, (n_tracks + 2) / 2)
                THEN tempo_corrected
            END
        ) AS median_corrected
    FROM ranked
    GROUP BY cohort_id
),
spread AS (
    SELECT
        t.cohort_id,
        SQRT(
            SUM((t.tempo_raw - m.mean_raw) * (t.tempo_raw - m.mean_raw))
            / (m.n_tracks - 1)
        ) AS sd_raw,
        SQRT(
            SUM((t.tempo_corrected - m.mean_corrected) * (t.tempo_corrected - m.mean_corrected))
            / (m.n_tracks - 1)
        ) AS sd_corrected
    FROM top_tracks AS t
    INNER JOIN moments AS m
        ON m.cohort_id = t.cohort_id
    GROUP BY t.cohort_id
)
SELECT
    moments.cohort_id,
    moments.n_tracks,
    moments.mean_raw,
    medians.median_raw,
    spread.sd_raw,
    moments.min_raw,
    moments.max_raw,
    moments.mean_corrected,
    medians.median_corrected,
    spread.sd_corrected,
    moments.mean_popularity,
    moments.min_popularity,
    moments.max_popularity,
    moments.n_octave_shifted,
    CAST(moments.n_octave_shifted AS REAL) / moments.n_tracks AS share_octave_shifted
FROM moments
INNER JOIN medians
    ON medians.cohort_id = moments.cohort_id
INNER JOIN spread
    ON spread.cohort_id = moments.cohort_id
ORDER BY moments.cohort_id;
