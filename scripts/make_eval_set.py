import csv, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
OUT = ROOT / "data" / "eval_set.csv"

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT c.id, r.normalized_name, r.normalized_domain,
               COALESCE(MAX(CASE WHEN f.field_name='homepage_text'
                                 THEN length(f.field_value) END), 0) AS text_len
        FROM companies c
        JOIN raw_sources r ON r.id = c.id
        LEFT JOIN company_fields f ON f.company_id = c.id
        GROUP BY c.id ORDER BY text_len ASC, c.id ASC""").fetchall()
    n = len(rows)
    picks = [rows[round(i * (n - 1) / 49)] for i in range(50)]   # 50 evenly spaced across the text-length range
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["company_id", "name", "domain", "text_len"])
        for cid, name, domain, tl in picks:
            w.writerow([cid, name, domain, tl])
    print(f"wrote {len(picks)} companies to {OUT}")
    print("text-length spread:", [p[3] for p in picks][:10], "...")

if __name__ == "__main__":
    main()
