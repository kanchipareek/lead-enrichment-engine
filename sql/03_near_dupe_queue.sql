INSERT INTO match_candidates
    (raw_source_id_a, raw_source_id_b, similarity_score, match_reason, reviewed, decision)
SELECT a.id, b.id, similarity(a.normalized_name, b.normalized_name), 'name_variant', 0, NULL
FROM raw_sources a
JOIN raw_sources b ON a.id < b.id
WHERE a.id = a.dedupe_group
  AND b.id = b.dedupe_group
  AND a.dedupe_group <> b.dedupe_group
  AND (a.normalized_domain IS NULL OR b.normalized_domain IS NULL
       OR a.normalized_domain <> b.normalized_domain)
  AND similarity(a.normalized_name, b.normalized_name) >= 0.75;

UPDATE match_candidates
SET decision = 'auto', reviewed = 1
WHERE decision IS NULL AND similarity_score >= 0.92;
