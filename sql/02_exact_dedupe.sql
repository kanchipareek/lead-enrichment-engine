UPDATE raw_sources SET match_method = 'first_seen' WHERE match_method IS NULL;

WITH ranked AS (
    SELECT id,
           MIN(id) OVER (
               PARTITION BY COALESCE(normalized_domain, 'name:' || normalized_name)
           ) AS grp
    FROM raw_sources
)
UPDATE raw_sources
SET dedupe_group = ranked.grp,
    match_method = CASE WHEN ranked.id <> ranked.grp THEN 'exact' ELSE match_method END,
    match_score  = CASE WHEN ranked.id <> ranked.grp THEN 1.0 ELSE match_score END
FROM ranked
WHERE raw_sources.id = ranked.id;
