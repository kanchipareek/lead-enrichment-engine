import re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
SKIP = {"features", "about", "contact", "topics", "sponsors", "orgs", "users",
        "settings", "login", "signup", "enterprise", "pricing", "security",
        "collections", "readme", "explore", "marketplace", "join"}

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT m.company_id, r.normalized_name, h.field_value
        FROM company_fields m
        JOIN company_fields h ON h.company_id = m.company_id AND h.field_name = 'homepage_text'
        JOIN raw_sources r ON r.id = m.company_id
        WHERE m.field_name = 'github_match' AND m.field_value = 'none'""").fetchall()
    print(f"{len(rows)} 'none' companies with homepage text - checking for self-linked GitHub orgs\n")
    for cid, name, text in rows:
        links = {l for l in re.findall(r"github\.com/([A-Za-z0-9-]+)/?", text or "")
                 if l.lower() not in SKIP}
        if links:
            print(f"{name}: {sorted(links)}  (company_id {cid})")

if __name__ == "__main__":
    main()
