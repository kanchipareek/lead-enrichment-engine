import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

# the data fields we care about (control fields like extraction_json / github_match excluded)
FIELDS = [
    "homepage_text", "homepage_title", "about_text", "careers_text", "product_text",
    "github_org", "github_org_blog", "github_repo_count", "github_total_stars",
    "github_top_repo", "github_top_repo_stars", "github_last_push", "github_last_release",
    "extracted_what_they_do", "extracted_category", "extracted_sells_to",
    "extracted_size_signal", "extracted_tech_signals",
]

expected = " UNION ALL ".join(f"SELECT id, '{f}' FROM companies" for f in FIELDS)

VIEW_SQL = f"""
DROP VIEW IF EXISTS field_quality;
CREATE VIEW field_quality AS
WITH expected(company_id, field_name) AS (
    {expected}
),
vals AS (
    SELECT company_id, field_name,
           COUNT(DISTINCT NULLIF(TRIM(field_value), '')) AS n_distinct,
           SUM(CASE WHEN TRIM(COALESCE(field_value,'')) NOT IN ('','unknown') THEN 1 ELSE 0 END) AS n_values,
           COUNT(*) AS n_rows,
           SUM(CASE WHEN TRIM(COALESCE(field_value,'')) = '' THEN 1 ELSE 0 END) AS n_empty,
           MAX(CASE WHEN source LIKE '%guess%' OR source LIKE '%unverified%' THEN 1 ELSE 0 END) AS unver
    FROM company_fields GROUP BY company_id, field_name
)
SELECT e.company_id, e.field_name,
    CASE
        WHEN v.n_distinct > 1                THEN 'conflicting'
        WHEN v.n_values >= 1 AND v.unver = 1 THEN 'unverified'
        WHEN v.n_values >= 1                 THEN 'usable'
        WHEN v.n_empty >= 1 AND e.field_name IN ('homepage_text','homepage_title','about_text','careers_text','product_text') THEN 'failed'
        ELSE 'missing'
    END AS quality_state
FROM expected e LEFT JOIN vals v
  ON v.company_id = e.company_id AND v.field_name = e.field_name;

DROP VIEW IF EXISTS crawl_failures;
CREATE VIEW crawl_failures AS
SELECT c.id AS company_id, c.name, l.url, l.status, l.fetched_at
FROM crawl_log l JOIN companies c ON c.id = l.company_id
WHERE l.ok = 0;
"""

conn = sqlite3.connect(DB)
conn.executescript(VIEW_SQL)
conn.commit()
print("views created: field_quality, crawl_failures\n")

print("field_quality states:")
for state, n in conn.execute("SELECT quality_state, COUNT(*) FROM field_quality GROUP BY quality_state ORDER BY 2 DESC"):
    print(f"  {state:<12} {n}")

print("\nper-field usable counts:")
for fn, n in conn.execute("SELECT field_name, SUM(quality_state='usable') FROM field_quality GROUP BY field_name ORDER BY 2 DESC"):
    print(f"  {fn:<26} {n}")

print("\ncrawl failures logged:", conn.execute("SELECT COUNT(*) FROM crawl_failures").fetchone()[0])
