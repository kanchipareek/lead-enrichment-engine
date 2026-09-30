import json, os, sqlite3, time, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse

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
                wait = int(e.headers.get("Retry-After") or 60)
                print(f"  rate limited - waiting {wait}s", flush=True)
                time.sleep(min(wait, 120) + 5)
                continue
            raise
        except Exception:
            if attempt == 4: raise
            time.sleep(10)
    raise RuntimeError("gave up after 5 tries")

def clean_domain(u):
    u = (u or "").strip().lower()
    if not u: return ""
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    d = urlparse(u).netloc
    return d[4:] if d.startswith("www.") else d

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT m.company_id, r.normalized_domain, o.field_value AS login
        FROM company_fields m
        JOIN company_fields o ON o.company_id = m.company_id AND o.field_name = 'github_org'
        JOIN raw_sources r ON r.id = m.company_id
        WHERE m.field_name = 'github_match' AND m.field_value = 'fuzzy'""").fetchall()
    print(f"{len(rows)} fuzzy matches to verify")
    for k, (cid, domain, login) in enumerate(rows, 1):
        print(f"[{k}/{len(rows)}] {login}", flush=True)
        org = api(f"https://api.github.com/users/{login}")
        blog = clean_domain(org.get("blog", ""))
        if domain and blog == domain:
            conn.execute("UPDATE company_fields SET field_value='verified' "
                         "WHERE company_id=? AND field_name='github_match'", (cid,))
            conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                         "VALUES (?,?,?,?,?,datetime('now'))",
                         (cid, "github_org_blog", blog, "github", org.get("html_url", "")))
        conn.commit()
        time.sleep(1.0)
    print("new split:", conn.execute(
        "SELECT field_value, COUNT(*) FROM company_fields WHERE field_name='github_match' "
        "GROUP BY field_value").fetchall())

if __name__ == "__main__":
    main()
