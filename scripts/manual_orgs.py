# manual GitHub org additions found during human review
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

# append (company domain, github org login) as I find them during review

ADDS = [
    ("6sense.com", "6si"),            # verified: blog 6sense.com
    ("arato.ai", "AratoAi"),          # verified: official SDK repos
    ("baseten.co", "basetenlabs"),    # verified: blog baseten.co, 1.2k-star truss
    ("bespokelabs.ai", "bespokelabsai"),  # verified: blog bespokelabs.ai
    ("braze.com", "braze-inc"),       # verified: blog braze.com, all SDKs
    ("flocksafety.com", "flocksafety"),    # verified: FedRAMP platform repos
    ("stytch.com", "stytchauth"),     # verified: blog stytch.com, official SDKs
    ("unkey.com", "unkeyed"),         # verified: blog unkey.com, 5.4k-star repo
    ("fireworks.ai", "fw-ai"),        # verified: blog fireworks.ai
    ("render.com", "renderinc"),      # verified: blog render.com
    ("trychroma.com", "chroma-core"),     # chroma vector DB lives here
    ("convex.dev", "get-convex"),         # convex-backend lives here
    ("dagster.io", "dagster-io"),         # dagster project
    ("langchain.com", "langchain-ai"),    # langchain project
    ("modal.com", "modal-labs"),          # modal-client lives here
    ("sentry.io", "getsentry"),           # the sentry project
    ("temporal.io", "temporalio"),        # temporal project
    ("github.com", "github"),             # the company itself
]


def main():
    conn = sqlite3.connect(DB)
    for domain, login in ADDS:
        row = conn.execute("SELECT id FROM companies WHERE domain = ?", (domain,)).fetchone()
        if not row:
            print(f"!! no company with domain {domain} - check the domain spelling")
            continue
        cid = row[0]
        existing = conn.execute(
            "SELECT 1 FROM company_fields WHERE company_id=? AND field_name='github_org' AND field_value=?",
            (cid, login)).fetchone()
        if existing:
            print(f"already added: {domain} -> {login}")
            continue
        conn.execute("UPDATE company_fields SET field_value='manual', source_url=? "
                     "WHERE company_id=? AND field_name='github_match'",
                     (f"https://github.com/{login}", cid))
        conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                     "VALUES (?,?,?,?,?,datetime('now'))",
                     (cid, "github_org", login, "manual", f"https://github.com/{login}"))
        print(f"added: {domain} -> {login} (manual)")
    conn.commit()
    print("split now:", conn.execute(
        "SELECT field_value, COUNT(*) FROM company_fields WHERE field_name='github_match' "
        "GROUP BY field_value").fetchall())

if __name__ == "__main__":
    main()
