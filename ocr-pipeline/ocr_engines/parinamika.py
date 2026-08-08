"""Adapter for Parinamika / Akshar Anveshini (IIT Bombay Sanskrit OCR).

As of writing this tool has no public API or CLI — it's a login-gated web
app (https://www.cse.iitb.ac.in/~ocr/) where you upload a PDF/page images
and read the OCR result back in the browser. Credentials are granted on
request by the project (contact: Prof. Pushpak Bhattacharyya, CFILT, IIT
Bombay), and nothing is documented about batch/programmatic access.

Given that, this adapter supports three modes, configured in .env:

  PARINAMIKA_MODE=file
  PARINAMIKA_INPUT_DIR=/path/to/dir
    The realistic mode today: run pages through the Parinamika web UI
    yourself, export/copy the OCR text, and drop one file per page into
    PARINAMIKA_INPUT_DIR, named to match the rendered page filename, e.g.
    page-017.txt (plain text) or page-017.json (structured, see
    _parse_payload). The pipeline picks each file up by page number as it
    processes that page, and falls back to Google Vision for any page
    whose file isn't there yet — so you can backfill incrementally.

  PARINAMIKA_MODE=cli / PARINAMIKA_MODE=http
    For if/when IIT Bombay provides a real programmatic interface. Fill in
    PARINAMIKA_CLI_CMD or PARINAMIKA_HTTP_URL and _parse_payload once the
    real request/response shape is known — nothing else in the pipeline
    needs to change.

If PARINAMIKA_MODE is unset, this engine raises EngineUnavailableError for
every page so the pipeline falls back to Google Vision automatically.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import requests

import config
from schemas import OCRBlock, PageOCRResult

from .base import EngineUnavailableError, OCREngine


class ParinamikaEngine(OCREngine):
    name = "parinamika"

    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult:
        if config.PARINAMIKA_MODE == "file":
            return self._recognize_file(page_num)
        if config.PARINAMIKA_MODE == "cli":
            return self._recognize_cli(image_path, page_num)
        if config.PARINAMIKA_MODE == "http":
            return self._recognize_http(image_path, page_num)
        raise EngineUnavailableError(
            "PARINAMIKA_MODE not configured — set PARINAMIKA_MODE=file, =cli, or =http in .env"
        )

    def _recognize_file(self, page_num: int) -> PageOCRResult:
        if not config.PARINAMIKA_INPUT_DIR:
            raise EngineUnavailableError("PARINAMIKA_INPUT_DIR not set")

        input_dir = Path(config.PARINAMIKA_INPUT_DIR)
        json_path = input_dir / f"page-{page_num:03d}.json"
        txt_path = input_dir / f"page-{page_num:03d}.txt"

        if json_path.exists():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            return self._parse_payload(payload, page_num)

        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8")
            return PageOCRResult(page_num=page_num, engine=self.name, text=text)

        raise EngineUnavailableError(
            f"no Parinamika export found for page {page_num} in {input_dir} "
            f"(expected page-{page_num:03d}.txt or .json) — falling back for this page"
        )

    def _recognize_cli(self, image_path: Path, page_num: int) -> PageOCRResult:
        if not config.PARINAMIKA_CLI_CMD:
            raise EngineUnavailableError("PARINAMIKA_CLI_CMD not set")

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.json"
            cmd = config.PARINAMIKA_CLI_CMD.format(image=str(image_path), out=str(out_path))
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=120
                )
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                raise EngineUnavailableError(f"parinamika CLI failed to run: {e}") from e

            if result.returncode != 0:
                raise EngineUnavailableError(
                    f"parinamika CLI exited {result.returncode}: {result.stderr[:500]}"
                )

            if out_path.exists():
                payload = json.loads(out_path.read_text(encoding="utf-8"))
            else:
                # some CLIs print JSON to stdout instead of a file
                payload = json.loads(result.stdout)

            return self._parse_payload(payload, page_num)

    def _recognize_http(self, image_path: Path, page_num: int) -> PageOCRResult:
        if not config.PARINAMIKA_HTTP_URL:
            raise EngineUnavailableError("PARINAMIKA_HTTP_URL not set")

        headers = {}
        if config.PARINAMIKA_HTTP_API_KEY:
            headers["Authorization"] = f"Bearer {config.PARINAMIKA_HTTP_API_KEY}"

        try:
            with open(image_path, "rb") as f:
                resp = requests.post(
                    config.PARINAMIKA_HTTP_URL,
                    files={"image": f},
                    headers=headers,
                    timeout=60,
                )
        except requests.RequestException as e:
            raise EngineUnavailableError(f"parinamika HTTP call failed: {e}") from e

        if resp.status_code != 200:
            raise EngineUnavailableError(
                f"parinamika HTTP call returned {resp.status_code}: {resp.text[:500]}"
            )

        return self._parse_payload(resp.json(), page_num)

    def _parse_payload(self, payload: dict, page_num: int) -> PageOCRResult:
        # Expected shape (adjust once the real response format is known):
        # {"text": "...", "blocks": [{"text": "...", "bbox": [x0,y0,x1,y1], "confidence": 0.9}]}
        text = payload.get("text", "")
        blocks = [
            OCRBlock(
                text=b.get("text", ""),
                bbox=tuple(b.get("bbox", (0, 0, 0, 0))),
                confidence=b.get("confidence"),
            )
            for b in payload.get("blocks", [])
        ]
        return PageOCRResult(
            page_num=page_num, engine=self.name, text=text, blocks=blocks, raw=payload
        )
