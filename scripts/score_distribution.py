import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

for cfg in ("generic_b2b_saas", "devtools_ai_infra"):
    rows = c.execute("SELECT score, COUNT(*) FROM company_scores WHERE config_name=? GROUP BY score ORDER BY score DESC", (cfg,)).fetchall()
    total = sum(n for _, n in rows)
    print(f"\n{cfg}  (total {total})")
    print(f"  {'score':>5} {'count':>6} {'cumulative':>12}")
    cum = 0
    for score, n in rows:
        cum += n
        print(f"  {int(score):>5} {n:>6} {cum:>6}  ({100*cum/total:>4.0f}%)")
