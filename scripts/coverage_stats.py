import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

def main():
    conn = sqlite3.connect(DB)
    gh = {r[0] for r in conn.execute(
        "SELECT company_id FROM company_fields "
        "WHERE field_name = 'github_match' AND field_value IN ('exact','verified','manual')")}
    site = {r[0] for r in conn.execute(
        "SELECT company_id FROM company_fields WHERE field_name = 'homepage_text'")}
    allc = {r[0] for r in conn.execute("SELECT id FROM companies")}
    print("both (site + github):", len(gh & site))
    print("site only:           ", len(site - gh))
    print("github only:         ", len(gh - site))
    print("neither:             ", len(allc - gh - site))
    print("total companies:     ", len(allc))

if __name__ == "__main__":
    main()
