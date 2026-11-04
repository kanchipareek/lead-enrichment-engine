"""One command: python run.py  -> runs the whole pipeline in order.

  python run.py            run everything
  python run.py --force    delete and rebuild the database first (destructive)
"""
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "lead_enrichment.db"
PY = sys.executable

# Load .env so the child processes inherit the keys (stdlib only).
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

PIPELINE = [
    ["src/init_db.py"],
    ["scripts/import_raw.py", "data/raw_companies.csv"],
    ["scripts/run_sql.py", "sql/01_normalize.sql"],
    ["scripts/run_sql.py", "sql/02_exact_dedupe.sql"],
    ["scripts/run_sql.py", "sql/03_near_dupe_queue.sql"],
    ["scripts/run_sql.py", "sql/05_prefix_queue.sql"],
    ["scripts/resolve_matches.py"],          # human review of fuzzy pairs - before 04
    ["scripts/run_sql.py", "sql/04_canonicalize.sql"],
    ["scripts/run_sql.py", "sql/06_crawl_log.sql"],
    ["scripts/crawl.py"],
    ["scripts/github_find.py"],
    ["scripts/github_verify.py"],
    ["scripts/github_resolve.py"],           # human review of fuzzy orgs
    ["scripts/manual_orgs.py"],
    ["scripts/github_homepage_links.py"],
    ["scripts/github_stats.py"],
    ["scripts/extract.py"],
    ["scripts/run_sql.py", "sql/07_score.sql"],
    ["scripts/extract_contacts.py"],
    ["scripts/generate_candidates.py"],
]

# Steps that need an API key: skip with a message instead of failing the run.
NEEDS_KEY = {
    "scripts/extract.py": "GEMINI_API_KEY",
    "scripts/extract_contacts.py": "GROQ_API_KEY",
}


def main():
    force = "--force" in sys.argv
    if DB.exists() and not force:
        sys.exit(f"{DB} already exists. Re-run with --force to delete and rebuild it.")

    for args in PIPELINE:
        key = NEEDS_KEY.get(args[0])
        if key and not os.environ.get(key):
            print(f">> skipped {args[0]} ({key} not set)", flush=True)
            continue
        cmd = [PY] + args + (["--force"] if force and args[0] == "src/init_db.py" else [])
        print(">>", " ".join(cmd), flush=True)
        if subprocess.call(cmd, cwd=ROOT) != 0:
            sys.exit(f"step failed: {' '.join(cmd)}")
    print("done.")


if __name__ == "__main__":
    main()
