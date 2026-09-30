import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

def info(rs_id):
    return conn.execute("SELECT id, raw_name, normalized_domain, source_name "
                        "FROM raw_sources WHERE id=?", (rs_id,)).fetchone()

pending = conn.execute(
    "SELECT id, raw_source_id_a, raw_source_id_b, similarity_score FROM match_candidates "
    "WHERE decision IS NULL ORDER BY similarity_score DESC").fetchall()
manual_merges = 0
for mc_id, a, b, score in pending:
    ra, rb = info(a), info(b)
    print(f"\n#{mc_id}  score={score:.2f}")
    print(f"  A: {ra[1]!r:<30} domain={ra[2]!r:<25} src={ra[3]}")
    print(f"  B: {rb[1]!r:<30} domain={rb[2]!r:<25} src={rb[3]}
    cmd = input("  [m]erge / [r]eject: ").strip().lower()
    if cmd == "m":
        ga = conn.execute("SELECT dedupe_group FROM raw_sources WHERE id=?", (a,)).fetchone()[0]
        gb = conn.execute("SELECT dedupe_group FROM raw_sources WHERE id=?", (b,)).fetchone()[0]
        if ga != gb:
            keep, lose = min(ga, gb), max(ga, gb)
            conn.execute("UPDATE raw_sources SET match_method='manual', match_score=? WHERE id=?", (score, lose))
            conn.execute("UPDATE raw_sources SET dedupe_group=? WHERE dedupe_group=?", (keep, lose))
        conn.execute("UPDATE match_candidates SET decision='manual_merge', reviewed=1 WHERE id=?", (mc_id,))
        manual_merges += 1
    elif cmd == "r":
        conn.execute("UPDATE match_candidates SET decision='rejected', reviewed=1 WHERE id=?", (mc_id,))
    conn.commit()
print("\nmanual merges:", manual_merges)
