import sys, sqlite3
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

def similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

conn = sqlite3.connect(DB)
conn.create_function("similarity", 2, similarity)
conn.executescript(Path(sys.argv[1]).read_text(encoding="utf-8"))
conn.commit()
print(f"ran {sys.argv[1]} ok")
