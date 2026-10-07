import json, os, re, sqlite3, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
GROQ_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
PAGES = ["about_text", "careers_text", "homepage_text", "product_text"]
MAX_CHARS = 6000

PROMPT = """You extract PEOPLE from a company's own web pages.

Return ONLY JSON in exactly this shape:
{"people": [{"name": "Jane Doe", "title": "Head of Growth", "quote": "..."}]}

Rules:
- Include a person ONLY if BOTH their name and their role appear in the text below.
- "quote" must be a verbatim snippet from the text that contains that person's name.
- Use ONLY the text provided. No outside knowledge. Never guess or invent a name.
- If no named people with roles appear, return {"people": []}

TEXT:
{text}"""


def build_text(conn, cid):
    parts = []
    for p in PAGES:
        r = conn.execute(
            "SELECT field_value FROM company_fields WHERE company_id=? AND field_name=? "
            "ORDER BY rowid DESC LIMIT 1", (cid, p)).fetchone()
        if r and r[0] and r[0].strip() and r[0].strip().lower() != "unknown":
            parts.append(f"[{p}]\n{r[0][:MAX_CHARS]}")
    return "\n\n".join(parts)


def call(prompt):
    body = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(GROQ_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_KEY}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 2:
                time.sleep(30 * (attempt + 1))
                continue
            raise
    return None



def parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get("people", [])
    except Exception:
        return []


def main():
    if not GROQ_KEY:
        sys.exit("set GROQ_API_KEY first")
    conn = sqlite3.connect(DB)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_contacts ON contacts(company_id, name)")
    conn.execute("CREATE TABLE IF NOT EXISTS contact_runs (company_id INTEGER PRIMARY KEY, processed_at TEXT)")
    # mark the companies already done by the Gemini run so we don't redo them
    conn.execute("INSERT OR IGNORE INTO contact_runs (company_id, processed_at) "
                 "SELECT DISTINCT company_id, datetime('now') FROM contacts")
    conn.commit()
    done = {r[0] for r in conn.execute("SELECT company_id FROM contact_runs")}
    rows = conn.execute("SELECT id FROM companies ORDER BY id").fetchall()
    total = len(rows)
    found = 0
    for i, (cid,) in enumerate(rows, 1):
        if cid in done:
            continue
        text = build_text(conn, cid)
        if not text:
            conn.execute("INSERT OR IGNORE INTO contact_runs (company_id, processed_at) VALUES (?, datetime('now'))", (cid,))
            conn.commit()
            continue
        try:
            people = parse(call(PROMPT.replace("{text}", text)))
        except Exception as e:
            print(f"[{i}/{total}] company {cid}: failed ({e})")
            continue
        for p in people:
            name = (p.get("name") or "").strip()
            title = (p.get("title") or "").strip()
            if name:
                conn.execute(
                    "INSERT OR IGNORE INTO contacts (company_id, name, title, email_source, collected_at) "
                    "VALUES (?,?,?,?,datetime('now'))", (cid, name, title, "page"))
                found += 1
        conn.execute("INSERT OR IGNORE INTO contact_runs (company_id, processed_at) VALUES (?, datetime('now'))", (cid,))
        conn.commit()
        if people:
            print(f"[{i}/{total}] company {cid}: {len(people)} people")
    conn.commit()
    print(f"done this run: {found} contacts stored")


if __name__ == "__main__":
    main()
