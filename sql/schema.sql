PRAGMA foreign_keys = ON;

CREATE TABLE raw_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_url TEXT,
    raw_name TEXT NOT NULL,
    raw_domain TEXT,
    raw_data TEXT,
    collected_at TEXT NOT NULL
);

CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE company_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    collected_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, field_name, source)
);

CREATE TABLE merge_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_source_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    match_method TEXT NOT NULL,
    match_score REAL,
    merged_at TEXT NOT NULL,
    FOREIGN KEY (raw_source_id) REFERENCES raw_sources(id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE match_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_source_id_a INTEGER NOT NULL,
    raw_source_id_b INTEGER NOT NULL,
    similarity_score REAL NOT NULL,
    match_reason TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0,
    decision TEXT,
    FOREIGN KEY (raw_source_id_a) REFERENCES raw_sources(id),
    FOREIGN KEY (raw_source_id_b) REFERENCES raw_sources(id)
);

CREATE TABLE icp_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    config_name TEXT NOT NULL,
    score REAL NOT NULL,
    qualified INTEGER NOT NULL,
    reason TEXT,
    scored_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, config_name)
);

CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT,
    title TEXT,
    email TEXT,
    email_source TEXT,
    collected_at TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);