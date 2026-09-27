import csv, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

conn = sqlite3.connect(DB)
with open(ROOT / "data" / "raw_companies.csv", newline="", encoding="utf-8") as f:
    n = 0
    for row in csv.DictReader(f):
        name = (row.get("company name") or row.get("company_name")
                or row.get("name") or row.get("raw_name") or "").strip()
        if not name:
            continue
        conn.execute(
            """INSERT INTO raw_sources
               (source_name, source_url, raw_name, raw_domain, raw_data, collected_at)
               VALUES (?, NULL, ?, ?, NULL, datetime('now'))""",
            ((row.get("source") or "manual").strip(),
             name,
             (row.get("domain") or row.get("raw_domain") or "").strip() or None))
        n += 1
conn.commit()
print(f"imported {n}; total:",
      conn.execute("SELECT COUNT(*) FROM raw_sources").fetchone()[0])
