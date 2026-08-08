from abc import ABC, abstractmethod
from pathlib import Path

from schemas import PageOCRResult


class EngineUnavailableError(Exception):
    """Raised when an engine cannot be reached or isn't configured, so the
    pipeline should fall back to the next engine rather than treat the page
    as failed."""


class OCREngine(ABC):
    name: str

    @abstractmethod
    def recognize(self, image_path: Path, page_num: int) -> PageOCRResult: ...
