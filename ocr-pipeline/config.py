import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
PAGES_DIR = PROJECT_ROOT / "output" / "pages"
TEXT_DIR = PROJECT_ROOT / "output" / "text"
JSONL_DIR = PROJECT_ROOT / "output" / "jsonl"

PDF_RENDER_DPI = int(os.environ.get("PDF_RENDER_DPI", "400"))

# Parinamika / Akshar Anveshini (IIT Bombay) — pluggable, no fixed public API.
# Set exactly one of these once we have the real interface details.
PARINAMIKA_MODE = os.environ.get("PARINAMIKA_MODE")  # "cli" | "http" | None
PARINAMIKA_CLI_CMD = os.environ.get(
    "PARINAMIKA_CLI_CMD"
)  # e.g. "parinamika-ocr --lang san --input {image} --output {out}"
PARINAMIKA_HTTP_URL = os.environ.get("PARINAMIKA_HTTP_URL")
PARINAMIKA_HTTP_API_KEY = os.environ.get("PARINAMIKA_HTTP_API_KEY")

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LLM_MODEL = os.environ.get("NAVYA_LLM_MODEL", "claude-sonnet-5")

RUN_CROSS_CHECK = os.environ.get("NAVYA_RUN_CROSS_CHECK", "1") == "1"
CROSS_CHECK_SIMILARITY_THRESHOLD = float(os.environ.get("NAVYA_XCHECK_THRESHOLD", "0.75"))

for d in (PAGES_DIR, TEXT_DIR, JSONL_DIR):
    d.mkdir(parents=True, exist_ok=True)
