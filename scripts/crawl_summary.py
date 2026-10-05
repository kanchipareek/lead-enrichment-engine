import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")
q = lambda s: c.execute(s).fetchone()[0]

print("companies:                ", q("SELECT COUNT(*) FROM companies"))
print("crawl attempts (all):     ", q("SELECT COUNT(*) FROM crawl_log"))
print("  ok:                     ", q("SELECT COUNT(*) FROM crawl_log WHERE ok=1"))
print("  failed:                 ", q("SELECT COUNT(*) FROM crawl_log WHERE ok=0"))
print("companies with >=1 failure:", q("SELECT COUNT(DISTINCT company_id) FROM crawl_log WHERE ok=0"))
print("usable homepage_text:     ", q("SELECT COUNT(*) FROM field_quality WHERE field_name='homepage_text' AND quality_state='usable'"))
print("usable homepage_title:    ", q("SELECT COUNT(*) FROM field_quality WHERE field_name='homepage_title' AND quality_state='usable'"))
