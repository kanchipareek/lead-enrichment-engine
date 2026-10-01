import csv, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"
EVAL = ROOT / "data" / "eval_set.csv"
LABELS = ROOT / "data" / "eval_labels.csv"

# verdict definition: would you put this company on a qualified list for a
# generic B2B SaaS ICP? a = yes, r = clearly not, u = can't tell without digging

def main():
    conn = sqlite3.connect(DB)
    ids = [int(r["company_id"]) for r in csv.DictReader(open(EVAL))]
    done = set()
    if LABELS.exists():
        done = {int(r["company_id"]) for r in csv.DictReader(open(LABELS))}
    new_file = not LABELS.exists()
    out = open(LABELS, "a", newline="")
    w = csv.writer(out)
    if new_file:
        w.writerow(["company_id", "verdict", "note"])
    todo = [i for i in ids if i not in done]
    print(f"{len(todo)} of {len(ids)} left to label")
    for k, cid in enumerate(todo, 1):
        name, domain = conn.execute(
            "SELECT r.normalized_name, r.normalized_domain FROM companies c "
            "JOIN raw_sources r ON r.id = c.id WHERE c.id = ?", (cid,)).fetchone()
        t = conn.execute("SELECT field_value FROM company_fields "
                         "WHERE company_id = ? AND field_name = 'homepage_text'", (cid,)).fetchone()
        snippet = (t[0][:600].replace("\n", " ") if t else "(no homepage text - crawl failed or JS shell)")
        print(f"\n[{k}/{len(todo)}] {name}  ({domain})\n{'-'*60}\n{snippet}\n{'-'*60}")
        while True:
            v = input("verdict [a]ccept / [r]eject / [u]nsure / [s]kip: ").strip().lower()
            if v in ("a", "r", "u", "s"):
                break
            print("type a, r, u or s")
        if v == "s":
            continue
        note = input("one-line reason (optional): ").strip()
        w.writerow([cid, {"a": "accept", "r": "reject", "u": "unsure"}[v], note])
        out.flush()
    out.close()
    print(f"\nlabels saved to {LABELS}")

if __name__ == "__main__":
    main()
