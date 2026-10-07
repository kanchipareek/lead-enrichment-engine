import re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

# how common each corporate pattern is (higher = more likely the real one)
RELIABILITY = {
    "first.last": 70,
    "first": 65,
    "flast": 60,
    "firstl": 50,
    "first_last": 40,
    "first-last": 35,
}


def split_name(name):
    parts = re.split(r"\s+", (name or "").strip())
    if not parts or not parts[0]:
        return None, None
    first = re.sub(r"[^a-z]", "", parts[0].lower())
    if len(parts) == 1:
        return first, None
    last = re.sub(r"[^a-z]", "", parts[-1].lower())
    return first, last



def patterns(first, last, domain):
    if not last:
        return {f"{first}@{domain}": "first"}
    return {
        f"{first}.{last}@{domain}": "first.last",
        f"{first}@{domain}": "first",
        f"{first[0]}{last}@{domain}": "flast",
        f"{first}{last[0]}@{domain}": "firstl",
        f"{first}_{last}@{domain}": "first_last",
        f"{first}-{last}@{domain}": "first-last",
    }


def clean_domain(d):
    d = (d or "").strip().lower()
    d = d.replace("https://", "").replace("http://", "")
    return d.strip("/").split("/")[0]


def main():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS contact_candidates (
      id INTEGER PRIMARY KEY, contact_id INT, email TEXT, source TEXT,
      pattern TEXT, reliability REAL, status TEXT, created_at TEXT);
    CREATE UNIQUE INDEX IF NOT EXISTS ux_candidates ON contact_candidates(contact_id, email);
    """)

    rows = conn.execute("""
        SELECT ct.id, ct.name, co.domain
        FROM contacts ct JOIN companies co ON co.id = ct.company_id
        WHERE co.domain IS NOT NULL AND TRIM(co.domain) <> ''
    """).fetchall()

    n = 0
    for cid, name, domain in rows:
        domain = clean_domain(domain)
        first, last = split_name(name)
        if not first:
            continue
        for email, pat in patterns(first, last, domain).items():
            conn.execute(
                "INSERT OR IGNORE INTO contact_candidates "
                "(contact_id, email, source, pattern, reliability, status, created_at) "
                "VALUES (?,?,?,?,?,?,datetime('now'))",
                (cid, email, "pattern", pat, RELIABILITY[pat], "unverified"))
            n += 1
    conn.commit()

    # ---- the waterfall: rank each contact's candidates, best wins ----
    conn.executescript("""
    DROP VIEW IF EXISTS email_waterfall;
    CREATE VIEW email_waterfall AS
    SELECT contact_id, email, source, pattern, reliability, status,
           ROW_NUMBER() OVER (
             PARTITION BY contact_id
             ORDER BY CASE status WHEN 'verified' THEN 0 WHEN 'unverified' THEN 1 ELSE 2 END,
                      reliability DESC
           ) AS rank
    FROM contact_candidates;

    DROP VIEW IF EXISTS best_email;
    CREATE VIEW best_email AS
    SELECT * FROM email_waterfall WHERE rank = 1;
    """)
    conn.commit()

    print(f"generated {n} candidate emails for {len(rows)} contacts")
    print("best-email picks:", conn.execute("SELECT COUNT(*) FROM best_email").fetchone()[0])


if __name__ == "__main__":
    main()
