import json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
SNAP = ROOT / "data" / "idempotency_snapshot.json"
TABLES = ["companies", "raw_sources", "company_fields", "merge_log", "match_candidates"]

def snapshot():
    conn = sqlite3.connect(DB)
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}

if "--before" in sys.argv:
    s = snapshot()
    json.dump(s, open(SNAP, "w"))
    print("before:", s)
elif "--after" in sys.argv:
    before = json.load(open(SNAP))
    after = snapshot()
    print("before:", before)
    print("after: ", after)
    print("IDEMPOTENT" if before == after else "NOT IDEMPOTENT")
    for t in TABLES:
        if before.get(t) != after.get(t):
            print(f"  {t}: {before[t]} -> {after[t]}")
else:
    print("usage: python scripts/check_idempotency.py --before | --after")

