import json, os, sqlite3, time, urllib.request, urllib.error
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
                 "VALUES (?,?,?,?,?,datetime('now'))", (cid, name, str(value), "github", url or ""))

def main():
    conn = sqlite3.connect(DB)
    done = {r[0] for r in conn.execute("SELECT company_id FROM company_fields WHERE field_name='github_repo_count'")}
    rows = conn.execute("SELECT company_id, field_value FROM company_fields "
                         "WHERE field_name='github_org' AND company_id NOT IN (%s) "
                         "ORDER BY company_id" % (",".join(map(str, done)) or "-1")).fetchall()
    print(f"{len(rows)} orgs to fetch stats for")
    for k, (cid, login) in enumerate(rows, 1):
        print(f"[{k}/{len(rows)}] {login}", flush=True)
        try:
            repos = api(f"https://api.github.com/orgs/{login}/repos?per_page=100&sort=pushed")
        except Exception as e:
            print(f"  failed: {e} - skipping, nothing written", flush=True)
            continue
        if not repos:
            field(conn, cid, "github_repo_count", 0, f"https://github.com/{login}")
            conn.commit()
            time.sleep(1.0)
            continue
        url = f"https://github.com/{login}"
        top = max(repos, key=lambda r: r["stargazers_count"])
        field(conn, cid, "github_repo_count", len(repos), url)
        field(conn, cid, "github_total_stars", sum(r["stargazers_count"] for r in repos), url)
        field(conn, cid, "github_top_repo", top["name"], top["html_url"])
        field(conn, cid, "github_top_repo_stars", top["stargazers_count"], top["html_url"])
        field(conn, cid, "github_last_push", top["pushed_at"], top["html_url"])
        try:
            rel = api(f"https://api.github.com/repos/{login}/{top['name']}/releases/latest")
            if rel:
                field(conn, cid, "github_last_release", rel.get("published_at", ""), rel.get("html_url", ""))
        except Exception:
            pass    # no release published = field stays absent
        conn.commit()
        time.sleep(1.0)
    print("done")

if __name__ == "__main__":
    main()
