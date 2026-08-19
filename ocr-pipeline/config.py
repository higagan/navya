import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
PAGES_DIR = PROJECT_ROOT / "output" / "pages"
TEXT_DIR = PROJECT_ROOT / "output" / "text"
JSONL_DIR = PROJECT_ROOT / "output" / "jsonl"

PDF_RENDER_DPI = int(os.environ.get("PDF_RENDER_DPI", "400"))

# Parinamika / Akshar Anveshini (IIT Bombay) — no public API, see
# ocr_engines/parinamika.py for what each mode means.
PARINAMIKA_MODE = os.environ.get("PARINAMIKA_MODE")  # "file" | "cli" | "http" | None
PARINAMIKA_INPUT_DIR = os.environ.get("PARINAMIKA_INPUT_DIR")
PARINAMIKA_CLI_CMD = os.environ.get(
    "PARINAMIKA_CLI_CMD"
)  # e.g. "parinamika-ocr --lang san --input {image} --output {out}"
PARINAMIKA_HTTP_URL = os.environ.get("PARINAMIKA_HTTP_URL")
PARINAMIKA_HTTP_API_KEY = os.environ.get("PARINAMIKA_HTTP_API_KEY")

GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

# Local/cloud vision-language models via Ollama, evaluated as an
# alternative OCR engine — see ocr_engines/ollama_vision.py.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
LLM_MODEL = os.environ.get("NAVYA_LLM_MODEL", "anthropic/claude-sonnet-5")

RUN_CROSS_CHECK = os.environ.get("NAVYA_RUN_CROSS_CHECK", "1") == "1"
CROSS_CHECK_SIMILARITY_THRESHOLD = float(os.environ.get("NAVYA_XCHECK_THRESHOLD", "0.75"))

# Structuring isn't perfectly reproducible run to run even at temperature=0
# (observed directly: the same block came back labelled differently between
# two otherwise-identical pipeline runs). >1 structures each page that many
# times and votes on the layer labels instead of trusting one call — see
# llm_postprocess.structure_page_consensus. Off by default since it multiplies
# LLM cost by this factor.
STRUCTURE_SAMPLES = int(os.environ.get("NAVYA_STRUCTURE_SAMPLES", "1"))

for d in (PAGES_DIR, TEXT_DIR, JSONL_DIR):
    d.mkdir(parents=True, exist_ok=True)
