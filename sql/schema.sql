PRAGMA foreign_keys = ON;
-- ============================================================
-- Lead enrichment engine - complete schema
-- Rebuilt from the live database (PRAGMA / sqlite_master).
-- This file is the single source of truth for the whole database,
-- including the Project 2 signal tables, because init_db.py
-- recreates the database from scratch.
-- ============================================================

-- ---------- intake ----------

CREATE TABLE raw_sources (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name       TEXT NOT NULL,
    source_url        TEXT,
    raw_name          TEXT NOT NULL,
    raw_domain        TEXT,
    raw_data          TEXT,
    collected_at      TEXT NOT NULL,
    normalized_name   TEXT,
    normalized_domain TEXT,
    dedupe_group      INTEGER,
    match_method      TEXT,
    match_score       REAL
);

-- ---------- identity ----------

CREATE TABLE companies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    domain     TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE company_fields (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL,
    field_name  TEXT NOT NULL,
    field_value TEXT,
    source      TEXT NOT NULL,
    source_url  TEXT,
    collected_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, field_name, source)
);

CREATE TABLE merge_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_source_id INTEGER NOT NULL,
    company_id    INTEGER NOT NULL,
    match_method  TEXT NOT NULL,
    match_score   REAL,
    merged_at     TEXT NOT NULL,
    FOREIGN KEY (raw_source_id) REFERENCES raw_sources(id),
    FOREIGN KEY (company_id)    REFERENCES companies(id)
);

CREATE TABLE match_candidates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_source_id_a  INTEGER NOT NULL,
    raw_source_id_b  INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    match_reason     TEXT,
    reviewed         INTEGER NOT NULL DEFAULT 0,
    decision         TEXT,
    FOREIGN KEY (raw_source_id_a) REFERENCES raw_sources(id),
    FOREIGN KEY (raw_source_id_b) REFERENCES raw_sources(id)
);

-- ---------- crawl ----------

CREATE TABLE crawl_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    url        TEXT NOT NULL,
    ok         INTEGER NOT NULL,
    status     TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------- contacts + email waterfall ----------

CREATE TABLE contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL,
    name         TEXT,
    title        TEXT,
    email        TEXT,
    email_source TEXT,
    collected_at TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE UNIQUE INDEX ux_contacts ON contacts(company_id, name);

CREATE TABLE contact_runs (
    company_id   INTEGER PRIMARY KEY,
    processed_at TEXT
);

CREATE TABLE contact_candidates (
    id          INTEGER PRIMARY KEY,
    contact_id  INT,
    email       TEXT,
    source      TEXT,
    pattern     TEXT,
    reliability REAL,
    status      TEXT,
    created_at  TEXT
);

CREATE UNIQUE INDEX ux_candidates ON contact_candidates(contact_id, email);

-- ---------- ICP scoring ----------

CREATE TABLE icp_configs (
    config_name TEXT,
    feature     TEXT,
    weight      REAL
);

CREATE TABLE icp_thresholds (
    config_name TEXT PRIMARY KEY,
    threshold   REAL
);

-- Legacy table: kept for compatibility, NOT populated.
-- Scoring is computed by the views below; read `qualified`.
CREATE TABLE icp_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL,
    config_name TEXT NOT NULL,
    score       REAL NOT NULL,
    qualified   INTEGER NOT NULL,
    reason      TEXT,
    scored_at   TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, config_name)
);

CREATE TABLE scoring_eval (
    company_id  INTEGER,
    config_name TEXT,
    score       REAL,
    human_label TEXT,
    labelled_at TEXT,
    PRIMARY KEY (company_id, config_name)
);

-- ---------- Project 2: market signals ----------

CREATE TABLE signals (
    id              INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    signal_type     TEXT    NOT NULL,              -- 'gtm_leadership_hire'
    source          TEXT    NOT NULL,              -- 'greenhouse'
    board_token     TEXT    NOT NULL,              -- which board the posting came from
    external_id     TEXT    NOT NULL,              -- the board's posting id
    source_url      TEXT    NOT NULL,              -- the posting URL (provenance)
    title           TEXT    NOT NULL,
    department      TEXT,
    matched_term    TEXT,                          -- which rule term fired
    seniority       TEXT,                          -- senior | director
    first_published TEXT,                          -- board's published date
    first_seen_at   TEXT    NOT NULL,              -- when P2 first saw it
    -- delivery state: the signal is written BEFORE any delivery attempt
    delivery_status TEXT    NOT NULL DEFAULT 'pending',  -- pending | delivered | failed
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    next_retry_at   TEXT,
    repost_of       INTEGER REFERENCES signals(id),
    UNIQUE (source, board_token, external_id, signal_type)
);

CREATE INDEX idx_signals_company ON signals(company_id);
CREATE INDEX idx_signals_status  ON signals(delivery_status, next_retry_at);

CREATE TABLE signal_deliveries (
    id            INTEGER PRIMARY KEY,
    signal_id     INTEGER NOT NULL REFERENCES signals(id),
    attempt_no    INTEGER NOT NULL,
    attempted_at  TEXT    NOT NULL,
    ok            INTEGER NOT NULL,                -- 1 success, 0 failure
    status_code   INTEGER,
    error         TEXT,
    next_retry_at TEXT
);

CREATE TABLE signal_candidates (
    id            INTEGER PRIMARY KEY,
    company_id    INTEGER NOT NULL REFERENCES companies(id),
    source        TEXT    NOT NULL,
    board_token   TEXT    NOT NULL,
    external_id   TEXT    NOT NULL,
    source_url    TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    department    TEXT,
    label         TEXT    NOT NULL,                -- 'near_miss' | 'review'
    reason        TEXT,                            -- why it did not qualify as a hit
    first_seen_at TEXT    NOT NULL,
    UNIQUE (source, board_token, external_id)
);

CREATE INDEX idx_candidates_label ON signal_candidates(label);

CREATE TABLE webhook_events (
    id              INTEGER PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    event           TEXT NOT NULL,
    payload         TEXT NOT NULL,
    received_at     TEXT NOT NULL
);

-- ============================================================
-- Views
-- ============================================================

-- Per-field quality state across the 18 expected fields.
CREATE VIEW field_quality AS
WITH expected(company_id, field_name) AS (
    SELECT id, 'homepage_text' FROM companies
    UNION ALL SELECT id, 'homepage_title'   FROM companies
    UNION ALL SELECT id, 'about_text'       FROM companies
    UNION ALL SELECT id, 'careers_text'     FROM companies
    UNION ALL SELECT id, 'product_text'     FROM companies
    UNION ALL SELECT id, 'github_org'       FROM companies
    UNION ALL SELECT id, 'github_org_blog'  FROM companies
    UNION ALL SELECT id, 'github_repo_count' FROM companies
    UNION ALL SELECT id, 'github_total_stars' FROM companies
    UNION ALL SELECT id, 'github_top_repo'  FROM companies
    UNION ALL SELECT id, 'github_top_repo_stars' FROM companies
    UNION ALL SELECT id, 'github_last_push' FROM companies
    UNION ALL SELECT id, 'github_last_release' FROM companies
    UNION ALL SELECT id, 'extracted_what_they_do' FROM companies
    UNION ALL SELECT id, 'extracted_category' FROM companies
    UNION ALL SELECT id, 'extracted_sells_to' FROM companies
    UNION ALL SELECT id, 'extracted_size_signal' FROM companies
    UNION ALL SELECT id, 'extracted_tech_signals' FROM companies
),
vals AS (
    SELECT company_id, field_name,
           COUNT(DISTINCT NULLIF(TRIM(field_value), '')) AS n_distinct,
           SUM(CASE WHEN TRIM(COALESCE(field_value,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END) AS n_values,
           COUNT(*) AS n_rows,
           SUM(CASE WHEN TRIM(COALESCE(field_value,'')) = '' THEN 1 ELSE 0 END) AS n_empty,
           MAX(CASE WHEN source LIKE '%guess%' OR source LIKE '%unverified%' THEN 1 ELSE 0 END) AS unver
    FROM company_fields
    GROUP BY company_id, field_name
)
SELECT e.company_id, e.field_name,
    CASE
        WHEN v.n_distinct > 1                THEN 'conflicting'
        WHEN v.n_values >= 1 AND v.unver = 1 THEN 'unverified'
        WHEN v.n_values >= 1                 THEN 'usable'
        WHEN v.n_empty >= 1 AND e.field_name IN
             ('homepage_text','homepage_title','about_text','careers_text','product_text') THEN 'failed'
        ELSE 'missing'
    END AS quality_state
FROM expected e
LEFT JOIN vals v
  ON v.company_id = e.company_id AND v.field_name = e.field_name;

CREATE VIEW crawl_failures AS
SELECT c.id AS company_id, c.name, l.url, l.status, l.fetched_at
FROM crawl_log l
JOIN companies c ON c.id = l.company_id
WHERE l.ok = 0;

CREATE VIEW email_waterfall AS
SELECT contact_id, email, source, pattern, reliability, status,
       ROW_NUMBER() OVER (
         PARTITION BY contact_id
         ORDER BY CASE status WHEN 'verified' THEN 0 WHEN 'unverified' THEN 1 ELSE 2 END,
                  reliability DESC
       ) AS rank
FROM contact_candidates;

CREATE VIEW best_email AS
SELECT * FROM email_waterfall WHERE rank = 1;

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
    FROM companies c
    LEFT JOIN company_fields f ON f.company_id = c.id
    GROUP BY c.id
)
SELECT company_id, 'sells_to_business' AS feature,
       CASE WHEN sells IN ('businesses','both') THEN 1 ELSE 0 END AS value FROM base
UNION ALL SELECT company_id, 'sells_to_consumer',
       CASE WHEN sells='consumers' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'has_tech_signals',
       CASE WHEN TRIM(COALESCE(tech,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'has_size_signal',
       CASE WHEN TRIM(COALESCE(size,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'has_github',
       CASE WHEN TRIM(COALESCE(gh_org,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'active_github',
       CASE WHEN last_push IS NOT NULL AND TRIM(last_push) <> ''
             AND julianday('now') - julianday(last_push) <= 180 THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'stars_100',
       CASE WHEN CAST(COALESCE(NULLIF(TRIM(stars),''),'0') AS INT) >= 100 THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'stars_500',
       CASE WHEN CAST(COALESCE(NULLIF(TRIM(stars),''),'0') AS INT) >= 500 THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_horizontal_saas',
       CASE WHEN cat='horizontal_saas' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_vertical_saas',
       CASE WHEN cat='vertical_saas' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_fintech',
       CASE WHEN cat='fintech' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_security',
       CASE WHEN cat='security' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_dev_tools',
       CASE WHEN cat='dev_tools' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_ai_infra',
       CASE WHEN cat='ai_infra' THEN 1 ELSE 0 END FROM base
UNION ALL SELECT company_id, 'cat_data_infra',
       CASE WHEN cat='data_infra' THEN 1 ELSE 0 END FROM base;

CREATE VIEW company_scores AS
SELECT ft.company_id, cfg.config_name, SUM(ft.value * cfg.weight) AS score
FROM company_features ft
JOIN icp_configs cfg ON cfg.feature = ft.feature
GROUP BY ft.company_id, cfg.config_name;

CREATE VIEW disqualified AS
SELECT company_id FROM company_features
WHERE feature='sells_to_consumer' AND value=1;

CREATE VIEW qualified AS
SELECT s.company_id, s.config_name, s.score, t.threshold
FROM company_scores s
JOIN icp_thresholds t ON t.config_name = s.config_name
WHERE s.score >= t.threshold
  AND s.company_id NOT IN (SELECT company_id FROM disqualified);

