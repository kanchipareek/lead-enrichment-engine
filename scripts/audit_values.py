import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

print(f"{'field':<26} {'null':>5} {'empty':>6} {'unknown':>8}")
for fn, nnull, nempty, nunk in conn.execute("""
    SELECT field_name,
           SUM(field_value IS NULL),
           SUM(TRIM(COALESCE(field_value,'')) = ''),
           SUM(TRIM(COALESCE(field_value,'')) = 'unknown')
    FROM company_fields GROUP BY field_name ORDER BY field_name
"""):
    print(f"{fn:<26} {nnull:>5} {nempty:>6} {nunk:>8}")
