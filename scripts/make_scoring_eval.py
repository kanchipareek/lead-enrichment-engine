import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
PER_BUCKET = 10  # set to 5 for a faster 30-company run

conn = sqlite3.connect(DB)
conn.executescript("""
CREATE TABLE IF NOT EXISTS scoring_eval (
  company_id INTEGER, config_name TEXT, score REAL,
  human_label TEXT, labelled_at TEXT,
  PRIMARY KEY (company_id, config_name));
""")

total = 0
for cfg, thr in conn.execute("SELECT config_name, threshold FROM icp_thresholds ORDER BY config_name"):
    buckets = [
        ("qualified", f"score >= {thr}"),
        ("near",      f"score >= {thr - 15} AND score < {thr}"),
        ("below",     f"score < {thr - 15}"),
    ]
    for bucket, cond in buckets:
        rows = conn.execute(
            f"SELECT company_id, score FROM company_scores "
            f"WHERE config_name = ? AND {cond} ORDER BY score DESC LIMIT ?",
            (cfg, PER_BUCKET)).fetchall()
        for cid, score in rows:
            conn.execute(
                "INSERT OR IGNORE INTO scoring_eval (company_id, config_name, score) VALUES (?,?,?)",
                (cid, cfg, score))
            total += 1
conn.commit()

print(f"sampled {total} (company, config) pairs for labelling")
for cfg, n, lab in conn.execute("""
    SELECT config_name, COUNT(*),
           SUM(CASE WHEN human_label IS NOT NULL THEN 1 ELSE 0 END)
    FROM scoring_eval GROUP BY config_name"""):
    print(f"  {cfg}: {n} sampled, {lab or 0} labelled")
print("\nnext:  python scripts/label_scoring.py")
