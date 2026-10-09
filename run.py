"""One command: python run.py  -> runs the whole pipeline in order."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PIPELINE = [
    ["python", "src/init_db.py"],
    ["python", "scripts/import_raw.py", "data/raw_companies.csv"],
    ["python", "scripts/run_sql.py", "sql/01_normalize.sql"],
    ["python", "scripts/run_sql.py", "sql/02_exact_dedupe.sql"],
    ["python", "scripts/run_sql.py", "sql/03_near_dupe_queue.sql"],
    ["python", "scripts/run_sql.py", "sql/04_canonicalize.sql"],
    ["python", "scripts/run_sql.py", "sql/05_prefix_queue.sql"],
    ["python", "scripts/run_sql.py", "sql/06_crawl_log.sql"],
    ["python", "scripts/crawl.py"],
    ["python", "scripts/github_find.py"],
    ["python", "scripts/github_verify.py"],
    ["python", "scripts/github_stats.py"],
    ["python", "scripts/extract.py"],
    ["python", "scripts/run_sql.py", "sql/07_score.sql"],
    ["python", "scripts/extract_contacts.py"],
    ["python", "scripts/generate_candidates.py"],
]


def main():
    for cmd in PIPELINE:
        print(">>", " ".join(cmd), flush=True)
        if subprocess.call(cmd, cwd=ROOT) != 0:
            sys.exit(f"step failed: {' '.join(cmd)}")
    print("done.")


if __name__ == "__main__":
    main()
