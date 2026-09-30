import json, os, sqlite3, sys, time, urllib.parse, urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"User-Agent": "lead-enrichment-bot/0.1 (portfolio project)",
           "Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"
DELAY = 2.5 if TOKEN else 7.0     # stay under 30/min (token) or 10/min (no token)

def api(url):
    import urllib.error
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):                    # rate limited: wait what GitHub asks
                wait = int(e.headers.get("Retry-After") or 60)
                print(f"  rate limited - waiting {wait}s", flush=True)
                time.sleep(min(wait, 120) + 5)
                continue
            raise
        except Exception:
            if attempt == 4: raise
            time.sleep(10)
    raise RuntimeError("gave up after 5 tries")

def field(conn, cid, name, value, url):
    conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                 "VALUES (?,?,?,?,?,datetime('now'))", (cid, name, value, "github", url or ""))

def find_org(name, domain):
    q = urllib.parse.quote(f"{name} type:org")
    items = api(f"https://api.github.com/search/users?q={q}&per_page=10").get("items", [])
    if not items:
        return None, None, "none"
    label = domain.split(".")[0] if domain else ""
    for it in items:                       # tier 1: exact - login IS the name or the domain label
        if it["login"].lower() == name or (label and it["login"].lower() == label):
            return it["login"], it["html_url"], "exact"
    best, best_s = None, 0.0              # tier 2: fuzzy - best similarity >= 0.75
    for it in items:
        s = SequenceMatcher(None, name, it["login"].lower()).ratio()
        if s > best_s: best, best_s = it, s
    if best and best_s >= 0.75:
        return best["login"], best["html_url"], "fuzzy"
    return None, None, "none"              # searched, found nothing worth proposing

def main():
    conn = sqlite3.connect(DB)
    done = {r[0] for r in conn.execute("SELECT company_id FROM company_fields WHERE field_name='github_match'")}
    rows = conn.execute(
        "SELECT c.id, r.normalized_name, r.normalized_domain FROM companies c "
        "JOIN raw_sources r ON r.id = c.id ORDER BY c.id").fetchall()
    todo = [(i, n, d) for i, n, d in rows if i not in done]
    print(f"{len(todo)} companies to match")
    for k, (cid, name, domain) in enumerate(todo, 1):
        print(f"[{k}/{len(todo)}] {name}", flush=True)
        login, url, method = find_org(name, domain)
        field(conn, cid, "github_match", method, url)
        if login:
            field(conn, cid, "github_org", login, url)
        conn.commit()
        time.sleep(DELAY)

if __name__ == "__main__":
    main()
