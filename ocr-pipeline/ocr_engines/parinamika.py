"""Adapter for Parinamika / Akshar Anveshini (IIT Bombay Sanskrit OCR).

There is no fixed public API for this tool as of writing — it's used here via
whichever interface is actually available (a local CLI binary, or an HTTP
endpoint if IIT Bombay exposes one). Configure exactly one mode in .env:

  PARINAMIKA_MODE=cli
  PARINAMIKA_CLI_CMD="parinamika-ocr --lang san --input {image} --output {out}"

  PARINAMIKA_MODE=http
  PARINAMIKA_HTTP_URL="https://.../ocr"
  PARINAMIKA_HTTP_API_KEY="..."

If PARINAMIKA_MODE is unset, this engine raises EngineUnavailableError for
every page so the pipeline falls back to Google Vision automatically. Fill in
the CLI/HTTP details once we have real access, without changing pipeline.py.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import requests

import config
from schemas import OCRBlock, PageOCRResult
from .base import OCREngine, EngineUnavailableError


class ParinamikaEngine(OCREngine):
    name = "parinamika"

    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult:
        if config.PARINAMIKA_MODE == "cli":
            return self._recognize_cli(image_path, page_num)
        if config.PARINAMIKA_MODE == "http":
            return self._recognize_http(image_path, page_num)
        raise EngineUnavailableError(
            "PARINAMIKA_MODE not configured — set PARINAMIKA_MODE=cli or =http in .env"
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
