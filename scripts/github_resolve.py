import json, os, sqlite3, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"User-Agent": "lead-enrichment-bot/0.1", "Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def api(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                print("  rate limited - waiting", flush=True)
                import time; time.sleep(60); continue
            raise
        except Exception:
            if attempt == 4: raise
            import time; time.sleep(10)
    raise RuntimeError("gave up")

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT m.company_id, r.normalized_name, r.normalized_domain, o.field_value AS login
        FROM company_fields m
        JOIN company_fields o ON o.company_id = m.company_id AND o.field_name = 'github_org'
        JOIN raw_sources r ON r.id = m.company_id
        WHERE m.field_name = 'github_match' AND m.field_value = 'fuzzy'
        ORDER BY r.normalized_name""").fetchall()
    print(f"{len(rows)} fuzzy matches to review")
    for k, (cid, name, domain, login) in enumerate(rows, 1):
        try:
            org = api(f"https://api.github.com/users/{login}")
        except Exception as e:
            print(f"[{k}/{len(rows)}] {name}: API failed ({e}), skipping")
            continue
        print(f"\n[{k}/{len(rows)}] company: {name}  ({domain})")
        print(f"  org: {login}")
        print(f"  org name: {org.get('name')}")
        print(f"  org blog: {org.get('blog')}")
        print(f"  org desc: {(org.get('description') or '')[:120]}")
        while True:
            ans = input("  [m]anual accept / [r]eject: ").strip().lower()
            if ans in ("m", "r"):
                break
            print("  type m or r - empty input is not a decision")
        if ans == "m":
            conn.execute("UPDATE company_fields SET field_value='manual' "
                         "WHERE company_id=? AND field_name='github_match'", (cid,))
        else:
            conn.execute("UPDATE company_fields SET field_value='none' "
                         "WHERE company_id=? AND field_name='github_match'", (cid,))
            conn.execute("DELETE FROM company_fields "
                         "WHERE company_id=? AND field_name='github_org'", (cid,))
            conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                         "VALUES (?,?,?,?,?,datetime('now'))",
                         (cid, "github_rejected_org", login, "manual_review",
                          f"https://github.com/{login}"))
        conn.commit()
    print("\nfinal split:", conn.execute(
        "SELECT field_value, COUNT(*) FROM company_fields WHERE field_name='github_match' "
        "GROUP BY field_value").fetchall())

if __name__ == "__main__":
    main()
