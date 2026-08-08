"""Adapter for local/cloud vision-language models served by Ollama.

Unlike Parinamika or Google Vision, these are general VLMs prompted to
transcribe text, not dedicated OCR engines with bounding-box output — so
results only ever populate PageOCRResult.text, never .blocks.

Configure the model in .env:
  OLLAMA_MODEL=qwen3-vl:8b        # or deepseek-ocr:3b, minicpm-v4.6, etc.
  OLLAMA_HOST=http://localhost:11434   # default, only needed to override
"""

import time
from pathlib import Path

import ollama

import config
from schemas import PageOCRResult

from .base import EngineUnavailableError, OCREngine

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3

TRANSCRIBE_PROMPT = (
    "Transcribe all text visible on this page image exactly as printed. "
    "This is a printed Sanskrit/Devanagari philosophy book page. "
    "Output ONLY the transcribed text, preserving line breaks and reading "
    "order (top to bottom). Do not translate, summarize, or explain "
    "anything. Do not add commentary. If a small page number is printed "
    "in a margin or header, include it exactly where it appears."
)


class OllamaVisionEngine(OCREngine):
    def __init__(self, model: str | None = None):
        self.model = model or config.OLLAMA_MODEL
        self.name = f"ollama:{self.model}"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.model:
                raise EngineUnavailableError("OLLAMA_MODEL not set")
            self._client = ollama.Client(host=config.OLLAMA_HOST)
        return self._client

    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult:
        client = self.client  # raises EngineUnavailableError immediately if unconfigured

        last_error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.chat(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": TRANSCRIBE_PROMPT,
                            "images": [str(image_path)],
                        }
                    ],
                )
                text = response["message"]["content"].strip()
                return PageOCRResult(page_num=page_num, engine=self.name, text=text)
            except Exception as e:
                # Cloud-hosted models go over the network per call and have
                # shown transient connection resets — worth a short retry,
                # same as the Google Vision engine.
                last_error = e
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise EngineUnavailableError(
            f"Ollama model {self.model} call failed after {MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error
