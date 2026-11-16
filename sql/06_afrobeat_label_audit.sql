-- Highest-popularity tracks labeled afrobeat in the source file.
-- on_african_lookup is 1 when the primary artist is on this project's list.
-- A 0 does not prove the artist is from outside Africa. The list is incomplete.
-- The point of the query is the head of the label: if the most popular rows
-- are not on the list, the genre string is not a stand-in for top African songs.
-- One row per track id, keeping the highest popularity copy.

WITH labeled AS (
    SELECT
        track_id,
        track_name,
        artists,
        primary_artist,
        popularity,
        tempo AS tempo_raw,
        track_genre,
        ROW_NUMBER() OVER (
            PARTITION BY track_id
            ORDER BY popularity DESC, track_id
        ) AS copy_rank
    FROM tracks_catalog
    WHERE track_genre = 'afrobeat'
),
deduped AS (
    SELECT
        track_id,
        track_name,
        artists,
        primary_artist,
        popularity,
        tempo_raw,
        track_genre
    FROM labeled
    WHERE copy_rank = 1
)
SELECT
    deduped.track_name,
    deduped.artists,
    deduped.primary_artist,
    deduped.popularity,
    deduped.tempo_raw,
    deduped.track_genre,
    CASE
        WHEN artist_lookup.artist_name IS NOT NULL THEN 1
        ELSE 0
    END AS on_african_lookup
FROM deduped
LEFT JOIN artist_lookup
    ON artist_lookup.artist_name = deduped.primary_artist
ORDER BY deduped.popularity DESC, deduped.track_id
LIMIT 25;
