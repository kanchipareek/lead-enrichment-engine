import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

TARGETS = {
    "generic_b2b_saas": {"horizontal_saas", "vertical_saas", "fintech", "security"},
    "devtools_ai_infra": {"dev_tools", "ai_infra", "data_infra"},
}
BUSINESS = {"businesses", "both", "unknown"}  # unknown audience is neutral, not a disqualifier

# Hand overrides - anything you want to label differently from the rule.
# e.g. genuinely-SaaS companies the extractor tagged category 'unknown':
OVERRIDES = {
    # ("Glean", "generic_b2b_saas"): "yes",
    # ("Mixpanel", "generic_b2b_saas"): "yes",
    # ("Atlassian", "generic_b2b_saas"): "yes",
}

conn = sqlite3.connect(DB)


def field(cid, name):
    r = conn.execute(
        "SELECT field_value FROM company_fields WHERE company_id=? AND field_name=? "
        "ORDER BY rowid DESC LIMIT 1", (cid, name)).fetchone()
    return (r[0] or "").strip().lower() if r and r[0] else ""


rows = conn.execute("""
    SELECT se.company_id, co.name, se.config_name
    FROM scoring_eval se JOIN companies co ON co.id = se.company_id""").fetchall()

for cid, name, cfg in rows:
    cat = field(cid, "extracted_category")
    sells = field(cid, "extracted_sells_to")
    label = "yes" if (cat in TARGETS[cfg] and sells in BUSINESS) else "no"
    if (name, cfg) in OVERRIDES:
        label = OVERRIDES[(name, cfg)]
    conn.execute(
        "UPDATE scoring_eval SET human_label=?, labelled_at=datetime('now') "
        "WHERE company_id=? AND config_name=?", (label, cid, cfg))
conn.commit()

print(f"applied rule-based labels to {len(rows)} pairs")
for cfg, y, n in conn.execute("""
    SELECT config_name, SUM(human_label='yes'), SUM(human_label='no')
    FROM scoring_eval GROUP BY config_name"""):
    print(f"  {cfg}: {y} yes, {n} no")

print("\nworth a second look (labelled 'no' but category is 'unknown'):")
found = False
for cid, name, cfg in rows:
    lab = conn.execute(
        "SELECT human_label FROM scoring_eval WHERE company_id=? AND config_name=?",
        (cid, cfg)).fetchone()[0]
    if lab == "no" and field(cid, "extracted_category") == "unknown":
        found = True
        print(f"  {name} [{cfg}]")
if not found:
    print("  none")

print("\nnext:  python scripts/eval_scoring.py")
