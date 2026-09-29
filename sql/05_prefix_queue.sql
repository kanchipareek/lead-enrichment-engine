INSERT INTO match_candidates (raw_source_id_a, raw_source_id_b, similarity_score, match_reason, reviewed, decision)
SELECT a.id, b.id, similarity(a.normalized_name, b.normalized_name), 'name_prefix', 0, NULL
FROM raw_sources a
JOIN raw_sources b ON a.id < b.id
WHERE a.id = a.dedupe_group
  AND b.id = b.dedupe_group
  AND a.dedupe_group <> b.dedupe_group
  AND (a.normalized_domain IS NULL OR b.normalized_domain IS NULL
       OR a.normalized_domain <> b.normalized_domain)
  AND NOT EXISTS (SELECT 1 FROM match_candidates m
                  WHERE (m.raw_source_id_a = a.id AND m.raw_source_id_b = b.id)
                     OR (m.raw_source_id_a = b.id AND m.raw_source_id_b = a.id))
  AND (
       (LENGTH(a.normalized_name) >= 4 AND b.normalized_name LIKE a.normalized_name || '%')
    OR (LENGTH(b.normalized_name) >= 4 AND a.normalized_name LIKE b.normalized_name || '%')
    OR (SUBSTR(REPLACE(a.normalized_name, '.', ' '), 1,
               INSTR(REPLACE(a.normalized_name, '.', ' ') || ' ', ' ') - 1)
      = SUBSTR(REPLACE(b.normalized_name, '.', ' '), 1,
               INSTR(REPLACE(b.normalized_name, '.', ' ') || ' ', ' ') - 1)
        AND LENGTH(SUBSTR(REPLACE(a.normalized_name, '.', ' '), 1,
               INSTR(REPLACE(a.normalized_name, '.', ' ') || ' ', ' ') - 1)) >= 4)
  );
