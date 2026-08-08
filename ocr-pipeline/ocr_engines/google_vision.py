import time
from pathlib import Path

from google.cloud import vision

import config
from schemas import OCRBlock, PageOCRResult

from .base import EngineUnavailableError, OCREngine

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


class GoogleVisionEngine(OCREngine):
    name = "google_vision"

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not config.GOOGLE_APPLICATION_CREDENTIALS:
                raise EngineUnavailableError(
                    "GOOGLE_APPLICATION_CREDENTIALS not set — see "
                    "https://cloud.google.com/vision/docs/setup"
                )
            self._client = vision.ImageAnnotatorClient()
        return self._client

    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult:
        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)
        # document_text_detection is the dense-text mode (vs plain text_detection),
        # correct choice for full pages of printed text rather than sparse labels.
        image_context = vision.ImageContext(language_hints=["sa", "hi"])

        response = None
        last_error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.client.document_text_detection(
                    image=image, image_context=image_context
                )
                break
            except Exception as e:
                # Transient network blips (connection resets, 503s) are common
                # against a remote API across hundreds of pages — worth a
                # short retry before giving up on the page.
                last_error = e
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        if response is None:
            raise EngineUnavailableError(
                f"Google Vision call failed after {MAX_ATTEMPTS} attempts: {last_error}"
            ) from last_error

        if response.error.message:
            raise EngineUnavailableError(f"Google Vision API error: {response.error.message}")

        annotation = response.full_text_annotation
        text = annotation.text

        blocks = []
        for page in annotation.pages:
            for block in page.blocks:
                block_text = "".join(
                    "".join(symbol.text for symbol in word.symbols) + " "
                    for paragraph in block.paragraphs
                    for word in paragraph.words
                ).strip()
                vertices = block.bounding_box.vertices
                xs = [v.x for v in vertices]
                ys = [v.y for v in vertices]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                blocks.append(OCRBlock(text=block_text, bbox=bbox, confidence=block.confidence))

        return PageOCRResult(page_num=page_num, engine=self.name, text=text, blocks=blocks)
