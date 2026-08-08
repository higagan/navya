from .base import OCREngine, EngineUnavailableError
from .parinamika import ParinamikaEngine
from .google_vision import GoogleVisionEngine

try:
    from .paddle_ocr import PaddleOCREngine
except ImportError:
    PaddleOCREngine = None

__all__ = [
    "OCREngine",
    "EngineUnavailableError",
    "ParinamikaEngine",
    "GoogleVisionEngine",
    "PaddleOCREngine",
]
