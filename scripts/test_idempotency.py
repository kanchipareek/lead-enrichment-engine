"""Prove the clean step is idempotent: re-running every sql/ file must not
create duplicates. Writes a backup first; restores nothing automatically.
"""
import shutil, sqlite3
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
BACKUP = ROOT / "data" / "lead_enrichment.pre_idempotency.db"
SQL_DIR = ROOT / "sql"          # was ROOT/"scripts"/"sql" - that folder does not exist

shutil.copy(DB, BACKUP)
print(f"backup written: {BACKUP.name}")

conn = sqlite3.connect(DB)

# sql/03 and sql/05 call similarity(a, b). run_sql.py registers it, so we must too.
conn.create_function(
    "similarity", 2,
    lambda a, b: SequenceMatcher(None, a or "", b or "").ratio(),
)

def n(table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

files = [f for f in sorted(SQL_DIR.glob("*.sql")) if f.name != "schema.sql"]
if not files:
    raise SystemExit(f"no .sql files found in {SQL_DIR} - refusing to report a pass")

before_companies = n("companies")
before_candidates = n("match_candidates")
print(f"\nbefore: {before_companies} companies, {before_candidates} candidates")

print(f"re-running {len(files)} sql file(s)")
for f in files:
    print(f"  running {f.name}")
    conn.executescript(f.read_text())
conn.commit()

after_companies = n("companies")
after_candidates = n("match_candidates")
print(f"after:  {after_companies} companies, {after_candidates} candidates")

ok = before_companies == after_companies and before_candidates == after_candidates
if ok:
    print("\nIDEMPOTENT - re-running clean changed nothing.")
else:
    print("\nNOT IDEMPOTENT")
    print(f"  companies:  {before_companies} -> {after_companies}")
    print(f"  candidates: {before_candidates} -> {after_candidates}")
    print(f"Restore:  cp {BACKUP.name} {DB.name}   (both in data/)")
