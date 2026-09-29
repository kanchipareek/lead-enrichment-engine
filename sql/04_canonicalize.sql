INSERT INTO companies (id, name, domain, created_at, updated_at)
SELECT dedupe_group, raw_name, raw_domain, datetime('now'), datetime('now')
FROM raw_sources
WHERE id = dedupe_group;

INSERT INTO merge_log (raw_source_id, company_id, match_method, match_score, merged_at)
SELECT id, dedupe_group, COALESCE(match_method, 'first_seen'), match_score, datetime('now')
FROM raw_sources;
