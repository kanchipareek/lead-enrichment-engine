import csv, json, os, sqlite3, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
EVAL = ROOT / "data" / "eval_set.csv"
KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-3.5-flash"
DELAY = 12.0

PROMPT = """You extract structured facts about ONE company from text copied from that company's OWN website.

STRICT RULES:
- Use ONLY the text below. Never use outside knowledge about this company.
- If the text does not clearly state something, return "unknown". "unknown" is a valid, expected answer. Never guess.
- For every field you fill with a real value, include the page it came from and a short verbatim quote (<= 20 words) as evidence.
- If a field is "unknown", its evidence quote must be "".

Return ONLY valid JSON with exactly these keys:
{
  "what_they_do": "one sentence on what they sell, in their own terms, or unknown",
  "category": "one of dev_tools, ai_infra, data_infra, security, fintech, vertical_saas, horizontal_saas, other, unknown",
  "sells_to": "one of businesses, consumers, both, unknown",
  "size_signal": "any explicit size/scale mentioned (e.g. '500+ customers', 'team of 40'), or unknown",
  "tech_signals": ["short tags actually mentioned, e.g. open-source, API-first, self-hosted, SOC 2; empty list if none"],
  "evidence": {
    "what_they_do": {"page": "homepage|about|careers|product", "quote": "..."},
    "category": {"page": "homepage|about|careers|product", "quote": "..."},
    "sells_to": {"page": "homepage|about|careers|product", "quote": "..."},
    "size_signal": {"page": "homepage|about|careers|product", "quote": "..."}
  }
}

Do not invent. If the text does not state a field clearly, that field is "unknown". If in doubt, "unknown"."""

def api(url, payload):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:250]
            if e.code in (429, 500, 503):
                wait = int(e.headers.get("Retry-After") or 30)
                print(f"  {e.code} - {body} - waiting {wait}s", flush=True)
                time.sleep(min(wait, 120) + 5)
                continue
            raise
        except Exception:
            if attempt == 2:
                raise
            time.sleep(10)
    raise RuntimeError("gave up after 8 tries")



def build_text(conn, cid):
    pages = []
    for name, label in [("homepage_text","homepage"),("about_text","about"),
                        ("careers_text","careers"),("product_text","product")]:
        r = conn.execute("SELECT field_value FROM company_fields WHERE company_id=? AND field_name=?",
                         (cid, name)).fetchone()
        if r and r[0]:
            pages.append(f"[{label}] {r[0][:3000]}")
    return "\n\n".join(pages)

def main(eval_only=False):
    if not KEY:
        raise SystemExit("set GEMINI_API_KEY first: export GEMINI_API_KEY=...")
    conn = sqlite3.connect(DB)
    done = {r[0] for r in conn.execute("SELECT company_id FROM company_fields WHERE field_name='extraction_json'")}
    if eval_only:
        ids = [int(r["company_id"]) for r in csv.DictReader(open(EVAL))]
    else:
        ids = [r[0] for r in conn.execute(
            "SELECT DISTINCT company_id FROM company_fields WHERE field_name='homepage_text'")]
    ids = [i for i in ids if i not in done]
    print(f"{len(ids)} companies to extract")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    n_ok = n_unknown = 0
    for k, cid in enumerate(ids, 1):
        text = build_text(conn, cid)
        if not text:
            print(f"[{k}/{len(ids)}] company {cid}: no text - skipping (stays unknown)", flush=True)
            continue
        nm = conn.execute("SELECT normalized_name FROM raw_sources WHERE id=?", (cid,)).fetchone()
        print(f"[{k}/{len(ids)}] {nm[0] if nm else cid}", flush=True)
        payload = {"contents":[{"parts":[{"text": PROMPT + "\n\n--- PAGES ---\n" + text}]}],
                   "generationConfig":{"temperature":0, "responseMimeType":"application/json"}}
        try:
            resp = api(url, payload)
            raw = resp["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(raw)
        except Exception as e:
            print(f"  failed: {e} - nothing written", flush=True); time.sleep(DELAY); continue
        for field, key in [("extracted_what_they_do","what_they_do"),("extracted_category","category"),
                           ("extracted_sells_to","sells_to"),("extracted_size_signal","size_signal")]:
            val = data.get(key, "unknown")
            ev = (data.get("evidence") or {}).get(key, {}) or {}
            src = ev.get("page", "")
            conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                         "VALUES (?,?,?,?,?,datetime('now'))", (cid, field, str(val), "ai:"+str(src), str(src)))
            if field == "extracted_what_they_do" and str(val).strip().lower() == "unknown":
                n_unknown += 1
        ts = data.get("tech_signals") or []
        conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                     "VALUES (?,?,?,?,?,datetime('now'))", (cid, "extracted_tech_signals", ",".join(ts), "ai", ""))
        conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                     "VALUES (?,?,?,?,?,datetime('now'))", (cid, "extraction_json", raw, "ai", ""))
        conn.commit(); n_ok += 1
        time.sleep(DELAY)
    print(f"\ndone: {n_ok} extracted, {n_unknown} returned unknown for what_they_do")

if __name__ == "__main__":
    main(eval_only="--eval" in sys.argv)
