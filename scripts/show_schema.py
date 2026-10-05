import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

print("tables and columns:")
for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({name})")]
    print(f"  {name}: {', '.join(cols)}")

print("\nfield names stored in company_fields:")
for (fn,) in conn.execute("SELECT DISTINCT field_name FROM company_fields ORDER BY field_name"):
    print("  ", fn)
