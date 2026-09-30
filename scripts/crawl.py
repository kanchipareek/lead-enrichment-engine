import sqlite3, sys, time
import urllib.request, urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
UA = "lead-enrichment-bot/0.1 (portfolio project; contact: kanchipareek01@gmail.com)"
DELAY = 1.2          # seconds between ANY two requests (be a good citizen)
DOMAIN_DELAY = 3.0   # extra spacing between requests to the SAME domain
TIMEOUT = 10
MAX_BYTES = 2_000_000
MAX_TEXT = 20000     # store first 20k chars of text per page
RETRIES = 2

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.parts, self.links = "", [], []
        self._in_title, self._skip, self._href = False, 0, None
    def handle_starttag(self, tag, attrs):
        if tag == "title": self._in_title = True
        if tag in ("script", "style", "noscript"): self._skip += 1
        if tag == "a": self._href = dict(attrs).get("href")
    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        if tag in ("script", "style", "noscript") and self._skip: self._skip -= 1
        if tag == "a" and self._href is not None:
            self.links.append(self._href); self._href = None
    def handle_data(self, data):
        s = data.strip()
        if not s: return
        if self._in_title: self.title += " " + s
        elif not self._skip: self.parts.append(s)
    @property
    def text(self):
        return " ".join(self.parts)[:MAX_TEXT]

robots, last_seen, last_hit = {}, {}, {}

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(MAX_BYTES).decode("utf-8", errors="replace")

def allowed(url):
    host = urlparse(url).netloc
    if host not in robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.parse(http_get(f"https://{host}/robots.txt").splitlines())
        except Exception:
            rp.parse([])          # unreachable robots.txt -> treat as allow-all
        robots[host] = rp
    return robots[host].can_fetch(UA, url)

def get(url):
    wait = DELAY - (time.time() - last_seen.get("_", 0))
    if wait > 0: time.sleep(wait)
    host = urlparse(url).netloc
    wait = DOMAIN_DELAY - (time.time() - last_hit.get(host, -99))
    if wait > 0: time.sleep(wait)
    last_seen["_"], last_hit[host] = time.time(), time.time()
    err = None
    for attempt in range(RETRIES + 1):
        try:
            return http_get(url), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:200]
            time.sleep(2 * (attempt + 1))
    return None, err

def parse(html):
    p = Page(); p.feed(html); return p

def log(conn, cid, url, ok, status):
    conn.execute("INSERT INTO crawl_log (company_id, url, ok, status) VALUES (?,?,?,?)",
                 (cid, url, int(ok), status))

def field(conn, cid, name, value, url):
    conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                 "VALUES (?,?,?,?,?,datetime('now'))", (cid, name, value, "crawl", url))

TARGETS = [("about", "about_text"), ("careers", "careers_text"), ("product", "product_text")]

def crawl_company(conn, cid, name, domain):
    base = f"https://{domain}/"
    if not allowed(base):
        log(conn, cid, base, False, "robots_disallow"); return
    html, err = get(base)
    if html is None:
        log(conn, cid, base, False, err); return          # failure stays NULL - never guess
    log(conn, cid, base, True, "ok")
    home = parse(html)
    field(conn, cid, "homepage_title", home.title, base)
    field(conn, cid, "homepage_text", home.text, base)
    candidates = {kw: None for kw, _ in TARGETS}
    for href in home.links:
        absu = urljoin(base, href)
        if urlparse(absu).netloc != urlparse(base).netloc: continue
        for kw in candidates:
            if candidates[kw] is None and kw in absu.lower():
                candidates[kw] = absu
    for kw, fname in TARGETS:
        url = candidates[kw]
        if not url or not allowed(url): continue
        html, err = get(url)
        if html is None:
            log(conn, cid, url, False, err)                 # subpage failure = that field stays NULL
        else:
            log(conn, cid, url, True, "ok")
            field(conn, cid, fname, parse(html).text, url)

def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    conn = sqlite3.connect(DB)
    done = {r[0] for r in conn.execute(
        "SELECT DISTINCT company_id FROM company_fields WHERE field_name='homepage_title'")}
    rows = conn.execute("SELECT id, name, domain FROM companies "
                         "WHERE domain IS NOT NULL AND TRIM(domain) <> '' AND id NOT IN (%s) "
                         "ORDER BY id" % (",".join(map(str, done)) or "-1")).fetchall() \
           if done else conn.execute(
        "SELECT id, name, domain FROM companies WHERE domain IS NOT NULL AND TRIM(domain) <> '' ORDER BY id").fetchall()
    todo = rows[:limit] if limit else rows
    print(f"{len(rows)} to crawl, starting with {len(todo)}")
    for i, (cid, name, domain) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {name} ({domain})", flush=True)
        try:
            crawl_company(conn, cid, name, domain)
        except Exception as e:
            log(conn, cid, f"https://{domain}/", False, f"unexpected: {e}"[:200])
        conn.commit()

if __name__ == "__main__":
    main()
