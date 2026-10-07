import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

FIELDS = ("extracted_category", "extracted_sells_to", "extracted_tech_signals",
          "extracted_size_signal", "github_total_stars")


def field(conn, cid, name):
    r = conn.execute(
        "SELECT field_value FROM company_fields WHERE company_id=? AND field_name=? "
        "ORDER BY rowid DESC LIMIT 1", (cid, name)).fetchone()
    return r[0] if r and r[0] else "-"


conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT se.company_id, co.name, se.config_name, se.score
    FROM scoring_eval se JOIN companies co ON co.id = se.company_id
    WHERE se.human_label IS NULL
    ORDER BY se.config_name, se.score DESC""").fetchall()

print(f"{len(rows)} pairs left to label")
print("For each: would a GTM person at THIS ICP actually target this company?\n")

for cid, name, cfg, score in rows:
    print("=" * 64)
    print(f"  {name}   [{cfg}]   score {int(score)}")
    for f in FIELDS:
        print(f"    {f:<22} {field(conn, cid, f)}")
    ans = input("  fit? [y]es / [n]o / [s]kip / [q]uit: ").strip().lower()
    if ans == "q":
        break
    if ans in ("y", "n"):
        conn.execute(
            "UPDATE scoring_eval SET human_label=?, labelled_at=datetime('now') "
            "WHERE company_id=? AND config_name=?",
            ("yes" if ans == "y" else "no", cid, cfg))
        conn.commit()

done = conn.execute("SELECT COUNT(*) FROM scoring_eval WHERE human_label IS NOT NULL").fetchone()[0]
print(f"\nlabelled: {done}")
print("next:  python scripts/eval_scoring.py")
