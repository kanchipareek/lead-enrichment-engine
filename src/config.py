"""Central config. Secrets from the environment; everything else has a default
so the pipeline runs out of the box. Stdlib only - no python-dotenv needed."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Minimal .env loader (stdlib). Real env vars always win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv(ROOT / ".env")

# --- secrets: no defaults, set these in .env or your shell ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- database ---
DB_PATH = Path(os.environ.get("LEADS_DB", ROOT / "data" / "lead_enrichment.db"))

# --- crawl ---
CRAWL_DELAY = float(os.environ.get("CRAWL_DELAY", "1.2"))
CRAWL_DOMAIN_DELAY = float(os.environ.get("CRAWL_DOMAIN_DELAY", "3.0"))
CRAWL_TIMEOUT = int(os.environ.get("CRAWL_TIMEOUT", "10"))
CRAWL_MAX_BYTES = int(os.environ.get("CRAWL_MAX_BYTES", str(2 * 1024 * 1024)))
CRAWL_RETRIES = int(os.environ.get("CRAWL_RETRIES", "2"))
CRAWL_MAX_PAGES = int(os.environ.get("CRAWL_MAX_PAGES", "4"))
USER_AGENT = os.environ.get(
    "CRAWL_USER_AGENT",
    "lead-enrichment-engine/1.0 (+contact: you@example.com)")

# --- github ---
GITHUB_DELAY = float(os.environ.get("GITHUB_DELAY", "4.0"))

# --- ai ---
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
