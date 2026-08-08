"""Optional local fallback. Not the primary or secondary engine — only used
if explicitly wired into the pipeline's engine list. Requires:
  pip install paddleocr paddlepaddle
"""

from pathlib import Path

from paddleocr import PaddleOCR

from schemas import OCRBlock, PageOCRResult

from .base import EngineUnavailableError, OCREngine


class PaddleOCREngine(OCREngine):
    name = "paddle_ocr"

    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            try:
                # PP-OCRv4 multilingual Devanagari model
                self._ocr = PaddleOCR(use_angle_cls=True, lang="devanagari")
            except Exception as e:
                raise EngineUnavailableError(f"PaddleOCR init failed: {e}") from e
        return self._ocr

    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult:
        try:
            result = self.ocr.ocr(str(image_path), cls=True)
        except Exception as e:
            raise EngineUnavailableError(f"PaddleOCR run failed: {e}") from e

        blocks = []
        lines = []
        for line in result[0] or []:
            bbox_points, (text, confidence) = line
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            blocks.append(OCRBlock(text=text, bbox=bbox, confidence=confidence))
            lines.append(text)

        return PageOCRResult(
            page_num=page_num, engine=self.name, text="\n".join(lines), blocks=blocks
        )
