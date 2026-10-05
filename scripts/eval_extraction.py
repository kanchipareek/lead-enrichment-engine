import csv, json, sqlite3, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
LABELS = ROOT / "data" / "eval_labels.csv"

SOFTWARE_CATS = {"dev_tools","ai_infra","data_infra","security","fintech",
                 "vertical_saas","horizontal_saas","other"}
PAGE_FIELDS = {"homepage":"homepage_text","about":"about_text",
               "careers":"careers_text","product":"product_text"}

def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()

def get(conn, cid, field):
    r = conn.execute("SELECT field_value FROM company_fields WHERE company_id=? AND field_name=? "
                     "ORDER BY rowid DESC LIMIT 1", (cid, field)).fetchone()
    return r[0] if r else None

def main():
    conn = sqlite3.connect(DB)
    labels = list(csv.DictReader(open(LABELS)))

    def pages(cid):
        return {label: norm(get(conn, cid, f)) for label, f in PAGE_FIELDS.items()}

    agree = noext = missing_quote = 0
    cites_total = cites_traced = 0
    rows, samples = [], []
    for r in labels:
        cid = int(r["company_id"]); human = r["verdict"]
        raw = get(conn, cid, "extraction_json")
        cat = get(conn, cid, "extracted_category")
        sells = get(conn, cid, "extracted_sells_to")
        what = get(conn, cid, "extracted_what_they_do")
        if not raw:
            noext += 1
            rows.append((cid, human, "no-extract", "-", "-", "")); continue
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        if str(cat) in ("None","unknown","") or str(sells) in ("None","unknown",""):
            sysv = "unsure"
        elif cat in SOFTWARE_CATS and sells in ("businesses","both"):
            sysv = "accept"
        else:
            sysv = "reject"
        ok = (sysv == human); agree += ok
        pg = pages(cid); hay = " ".join(pg.values())
        ev = data.get("evidence") or {}
        for k in ("what_they_do","category","sells_to","size_signal"):
            val = str(data.get(k, "unknown")).lower()
            if val in ("unknown","none",""): continue
            cites_total += 1
            q = str((ev.get(k) or {}).get("quote","")).strip()
            if not q:
                missing_quote += 1
            else:
                nq = norm(q)
                if nq in hay or (len(nq) > 40 and nq[:40] in hay):
                    cites_traced += 1
        rows.append((cid, human, sysv, str(cat), str(sells), "" if ok else "  <-- differs"))
        if len(samples) < 6:
            samples.append((cid, what, (ev.get("what_they_do") or {}).get("quote","")))

    n = len(labels); with_ext = n - noext
    base = sum(1 for r in labels if r["verdict"] == "accept")
    print(f"eval set: {n} companies")
    print(f"  extraction present: {with_ext}   no extraction: {noext}")
    if with_ext:
        print(f"  verdict agreement: {agree}/{with_ext} = {100*agree/with_ext:.0f}%")
    print(f"  always-accept baseline: {100*base/n:.0f}%   (the honest comparison)")
    print(f"  filled fields missing a quote: {missing_quote}/{cites_total}")
    if cites_total:
        print(f"  citations tracing to source text: {cites_traced}/{cites_total} = {100*cites_traced/cites_total:.0f}%")
    print()
    print(f"{'cid':>4} {'human':<8} {'system':<9} {'category':<14} {'sells_to':<10}")
    for cid, human, sysv, cat, sells, flag in rows:
        print(f"{cid:>4} {human:<8} {sysv:<9} {cat:<14} {sells:<10}{flag}")
    print("\nSample (what_they_do + evidence quote):")
    for cid, what, quote in samples:
        print(f"  [{cid}] {what}")
        print(f'        "{str(quote)[:110]}"')

if __name__ == "__main__":
    main()
