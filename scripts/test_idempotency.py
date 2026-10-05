import shutil, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
BACKUP = ROOT / "data" / "lead_enrichment.backup.db"
SQL_DIR = ROOT / "scripts" / "sql"

# 1. back up first, so a non-idempotent re-run can't hurt you
shutil.copy(DB, BACKUP)
print(f"backup written: {BACKUP.name}")

conn = sqlite3.connect(DB)

def n(table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

before = n("companies")
print(f"\ncompanies BEFORE re-running clean: {before}")

# 2. re-run the clean step (every .sql file, in order)
for f in sorted(SQL_DIR.glob("*.sql")):
    print(f"  running {f.name}")
    conn.executescript(f.read_text())
conn.commit()

# 3. compare
after = n("companies")
print(f"companies AFTER re-running clean:  {after}")
if before == after:
    print("\nIDEMPOTENT - re-running clean created no duplicates. Done.")
else:
    print(f"\nNOT IDEMPOTENT - {after - before} extra companies appeared.")
    print("Restore your database:  cp data/lead_enrichment.backup.db data/lead_enrichment.db")