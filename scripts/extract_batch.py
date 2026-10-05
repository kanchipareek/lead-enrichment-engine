import csv, json, os, sqlite3, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
EVAL = ROOT / "data" / "eval_set.csv"
STATE = ROOT / "data" / "batch_state.json"
KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-3.7-flash"
BASE = "https://generativelanguage.googleapis.com/v1beta"

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

def call(method, path, payload=None, raw=False):
    sep = "&" if "?" in path else "?"
    url = f"{BASE}/{path}{sep}key={KEY}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read().decode()
            return b if raw else json.loads(b)
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, "-", e.read().decode()[:600]); raise

def build_text(conn, cid):
    pages = []
    for name, label in [("homepage_text","homepage"),("about_text","about"),
                        ("careers_text","careers"),("product_text","product")]:
        r = conn.execute("SELECT field_value FROM company_fields WHERE company_id=? AND field_name=?",
                         (cid, name)).fetchone()
        if r and r[0]:
            pages.append(f"[{label}] {r[0][:3000]}")
    return "\n\n".join(pages)

def store(conn, cid, raw):
    data = json.loads(raw)
    for field, key in [("extracted_what_they_do","what_they_do"),("extracted_category","category"),
                       ("extracted_sells_to","sells_to"),("extracted_size_signal","size_signal")]:
        val = data.get(key, "unknown")
        ev = (data.get("evidence") or {}).get(key, {}) or {}
        src = ev.get("page", "")
        conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                     "VALUES (?,?,?,?,?,datetime('now'))", (cid, field, str(val), "ai:"+str(src), str(src)))
    conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                 "VALUES (?,?,?,?,?,datetime('now'))",
                 (cid, "extracted_tech_signals", ",".join(data.get("tech_signals") or []), "ai", ""))
    conn.execute("INSERT INTO company_fields (company_id, field_name, field_value, source, source_url, collected_at) "
                 "VALUES (?,?,?,?,?,datetime('now'))", (cid, "extraction_json", raw, "ai", ""))
    conn.commit()

def submit(conn, ids):
    reqs, kept = [], []
    for cid in ids:
        text = build_text(conn, cid)
        if not text:
            print(f"  company {cid}: no text - skipping")
            continue
        reqs.append({"request": {"contents":[{"parts":[{"text": PROMPT + "\n\n--- PAGES ---\n" + text}]}],
                                 "generationConfig":{"temperature":0,"responseMimeType":"application/json"}}})
        kept.append(cid)
    print(f"submitting {len(reqs)} requests as one batch job")
    body = {"batch": {"display_name": "extract-eval",
                      "input_config": {"requests": {"requests": reqs}}}}
    out = call("POST", f"models/{MODEL}:batchGenerateContent", body)
    print("submission response:", json.dumps(out, indent=2)[:600])
    STATE.write_text(json.dumps({"name": out.get("name"), "ids": kept}))
    print("batch name:", out.get("name"))
    return out

def poll_and_store(conn):
    st = json.loads(STATE.read_text())
    name, ids = st["name"], st["ids"]
    while True:
        out = call("GET", name)
        state = (out.get("metadata") or {}).get("state") or out.get("state") or "?"
        print("state:", state, flush=True)
        if state == "BATCH_STATE_SUCCEEDED":
            break
        if state in ("BATCH_STATE_FAILED","BATCH_STATE_CANCELLED","BATCH_STATE_EXPIRED"):
            print("batch ended in", state, "- full response:")
            print(json.dumps(out, indent=2)[:1500]); return
        time.sleep(30)
    resp = out.get("response") or {}
    if resp.get("responses"):
        for cid, item in zip(ids, resp["responses"]):
            try:
                raw = item["response"]["candidates"][0]["content"]["parts"][0]["text"]
                store(conn, cid, raw)
            except Exception as e:
                print(f"  company {cid}: could not parse ({e})")
    elif resp.get("responsesFile"):
        fname = resp["responsesFile"]
        print("downloading results file:", fname)
        raw_text = call("GET", f"{fname}?alt=media", raw=True)
        for cid, line in zip(ids, raw_text.splitlines()):
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
                raw = obj["response"]["candidates"][0]["content"]["parts"][0]["text"]
                store(conn, cid, raw)
            except Exception as e:
                print(f"  company {cid}: could not parse ({e})")
    else:
        print("no inline responses or file found - full response:")
        print(json.dumps(out, indent=2)[:2000])
    STATE.unlink()
    print("done storing - state file cleared")

def main():
    if not KEY:
        raise SystemExit("set GEMINI_API_KEY first: export GEMINI_API_KEY=...")
    conn = sqlite3.connect(DB)
    if STATE.exists():
        print("found an existing batch job - polling it (Ctrl+C is safe; re-run to resume)")
        poll_and_store(conn); return
    done = {r[0] for r in conn.execute("SELECT company_id FROM company_fields WHERE field_name='extraction_json'")}
    if "--eval" in sys.argv:
        ids = [int(r["company_id"]) for r in csv.DictReader(open(EVAL))]
    else:
        ids = [r[0] for r in conn.execute("SELECT DISTINCT company_id FROM company_fields WHERE field_name='homepage_text'")]
    ids = [i for i in ids if i not in done]
    print(f"{len(ids)} companies to extract")
    submit(conn, ids)
    poll_and_store(conn)

if __name__ == "__main__":
    main()
