import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

print("Per config:")
for cfg, q, w in c.execute("""
    SELECT q.config_name,
           COUNT(DISTINCT q.company_id),
           COUNT(DISTINCT ct.company_id)
    FROM qualified q
    LEFT JOIN contacts ct ON ct.company_id = q.company_id
    GROUP BY q.config_name"""):
    print(f"  {cfg}: {q} qualified, {w} with at least one contact")

q = c.execute("SELECT COUNT(DISTINCT company_id) FROM qualified").fetchone()[0]
w = c.execute(
    "SELECT COUNT(DISTINCT q.company_id) FROM qualified q "
    "JOIN contacts ct ON ct.company_id = q.company_id").fetchone()[0]
print(f"\nAny config: {q} qualified accounts, {w} with at least one contact")

tot = c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
print(f"Total contacts: {tot}")
