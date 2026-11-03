import sqlite3
db = sqlite3.connect("data/lead_enrichment.db")
rows = db.execute("""
    SELECT s.company_id, c.name, s.config_name
    FROM icp_scores s JOIN companies c ON c.id = s.company_id
    ORDER BY RANDOM() LIMIT 30
""").fetchall()
for cid, name, cfg in rows:
    print(f"\n{name}  [{cfg}]")          # name + config ONLY - no score
    while True:
        ans = input("  fit? (y/n): ").strip().lower()
        if ans in ("y", "n"):
            db.execute("UPDATE scoring_eval SET human_label=?, labelled_at=datetime('now') "
                       "WHERE company_id=? AND config_name=?",
                       ("yes" if ans == "y" else "no", cid, cfg))
            db.commit()
            break
