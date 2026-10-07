-- ICP SCORING  (Project 1 - SCORE stage)
-- Two swappable configs: same features, different weights.

DROP TABLE IF EXISTS icp_configs;
CREATE TABLE icp_configs (config_name TEXT, feature TEXT, weight REAL);
INSERT INTO icp_configs (config_name, feature, weight) VALUES
 ('generic_b2b_saas','cat_horizontal_saas',40),
 ('generic_b2b_saas','cat_vertical_saas',  40),
 ('generic_b2b_saas','cat_fintech',        40),
 ('generic_b2b_saas','cat_security',       40),
 ('generic_b2b_saas','sells_to_business',  30),
 ('generic_b2b_saas','has_size_signal',    10),
 ('generic_b2b_saas','has_tech_signals',   15),
 ('generic_b2b_saas','stars_100',           5),
 ('devtools_ai_infra','cat_dev_tools',     35),
 ('devtools_ai_infra','cat_ai_infra',      35),
 ('devtools_ai_infra','cat_data_infra',    35),
 ('devtools_ai_infra','has_tech_signals',  25),
 ('devtools_ai_infra','active_github',     20),
 ('devtools_ai_infra','stars_500',         15),
 ('devtools_ai_infra','sells_to_business',  5);

DROP TABLE IF EXISTS icp_thresholds;
CREATE TABLE icp_thresholds (config_name TEXT PRIMARY KEY, threshold REAL);
INSERT INTO icp_thresholds (config_name, threshold) VALUES
 ('generic_b2b_saas',70),('devtools_ai_infra',70);

DROP VIEW IF EXISTS company_features;
CREATE VIEW company_features AS
WITH base AS (
    SELECT c.id AS company_id,
           MAX(CASE WHEN f.field_name='extracted_category'     THEN f.field_value END) AS cat,
           MAX(CASE WHEN f.field_name='extracted_sells_to'     THEN f.field_value END) AS sells,
           MAX(CASE WHEN f.field_name='extracted_tech_signals' THEN f.field_value END) AS tech,
           MAX(CASE WHEN f.field_name='extracted_size_signal'  THEN f.field_value END) AS size,
           MAX(CASE WHEN f.field_name='github_org'             THEN f.field_value END) AS gh_org,
           MAX(CASE WHEN f.field_name='github_total_stars'     THEN f.field_value END) AS stars,
           MAX(CASE WHEN f.field_name='github_last_push'       THEN f.field_value END) AS last_push
    FROM companies c LEFT JOIN company_fields f ON f.company_id = c.id
    GROUP BY c.id
)
SELECT company_id,'sells_to_business'   AS feature, CASE WHEN sells IN ('businesses','both') THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'sells_to_consumer'   AS feature, CASE WHEN sells='consumers' THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'has_tech_signals'    AS feature, CASE WHEN TRIM(COALESCE(tech,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'has_size_signal'     AS feature, CASE WHEN TRIM(COALESCE(size,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'has_github'          AS feature, CASE WHEN TRIM(COALESCE(gh_org,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'active_github'       AS feature, CASE WHEN last_push IS NOT NULL AND TRIM(last_push)<>'' AND julianday('now')-julianday(last_push)<=180 THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'stars_100'           AS feature, CASE WHEN CAST(COALESCE(NULLIF(TRIM(stars),''),'0') AS INT)>=100 THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'stars_500'           AS feature, CASE WHEN CAST(COALESCE(NULLIF(TRIM(stars),''),'0') AS INT)>=500 THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_horizontal_saas' AS feature, CASE WHEN cat='horizontal_saas' THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_vertical_saas'   AS feature, CASE WHEN cat='vertical_saas'   THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_fintech'         AS feature, CASE WHEN cat='fintech'         THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_security'        AS feature, CASE WHEN cat='security'        THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_dev_tools'       AS feature, CASE WHEN cat='dev_tools'       THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_ai_infra'        AS feature, CASE WHEN cat='ai_infra'        THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id,'cat_data_infra'      AS feature, CASE WHEN cat='data_infra'      THEN 1 ELSE 0 END AS value FROM base;

DROP VIEW IF EXISTS company_scores;
CREATE VIEW company_scores AS
SELECT ft.company_id, cfg.config_name, SUM(ft.value * cfg.weight) AS score
FROM company_features ft JOIN icp_configs cfg ON cfg.feature = ft.feature
GROUP BY ft.company_id, cfg.config_name;

DROP VIEW IF EXISTS disqualified;
CREATE VIEW disqualified AS
SELECT company_id FROM company_features WHERE feature='sells_to_consumer' AND value=1;

DROP VIEW IF EXISTS qualified;
CREATE VIEW qualified AS
SELECT s.company_id, s.config_name, s.score, t.threshold
FROM company_scores s JOIN icp_thresholds t ON t.config_name = s.config_name
WHERE s.score >= t.threshold
  AND s.company_id NOT IN (SELECT company_id FROM disqualified);
  
