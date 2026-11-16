-- Descriptive tempo by country inside the African top 100.
-- Country comes from the artist lookup, not from the source file.
-- Small groups are left in the result. Do not read a 5-track mean as a national tempo.
-- Median uses the same central-rank rule as the cohort summary.

WITH africa_top AS (
    SELECT
        country,
        region,
        track_id,
        tempo_raw,
        tempo_corrected
    FROM track_analysis
    WHERE is_top100 = 1
      AND cohort_id = 'africa_popular'
),
moments AS (
    SELECT
        country,
        region,
        COUNT(*) AS n_tracks,
        AVG(tempo_raw) AS mean_raw,
        AVG(tempo_corrected) AS mean_corrected
    FROM africa_top
    GROUP BY country, region
),
ranked AS (
    SELECT
        country,
        tempo_raw,
        ROW_NUMBER() OVER (
            PARTITION BY country
            ORDER BY tempo_raw, track_id
        ) AS rn_raw,
        COUNT(*) OVER (PARTITION BY country) AS n_tracks
    FROM africa_top
),
medians AS (
    SELECT
        country,
        AVG(
            CASE
                WHEN rn_raw IN ((n_tracks + 1) / 2, (n_tracks + 2) / 2)
                THEN tempo_raw
            END
        ) AS median_raw
    FROM ranked
    GROUP BY country
)
SELECT
    moments.country,
    moments.region,
    moments.n_tracks,
    moments.mean_raw,
    medians.median_raw,
    moments.mean_corrected
FROM moments
INNER JOIN medians
    ON medians.country = moments.country
ORDER BY moments.n_tracks DESC, moments.country;
