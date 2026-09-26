import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lead_enrichment.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

if DB_PATH.exists():
    DB_PATH.unlink()  


connection = sqlite3.connect(DB_PATH)

with open(SCHEMA_PATH, "r" , encoding="utf-8") as file:
    schema = file.read()

connection.executescript(schema)
connection.commit()
connection.close()

print(f"Database created at {DB_PATH}")

