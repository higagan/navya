from dataclasses import asdict, dataclass, field


@dataclass
class OCRBlock:
    text: str
    bbox: tuple  # (x0, y0, x1, y1) in image pixel coords
    confidence: float | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class PageOCRResult:
    page_num: int  # 1-indexed PDF page number
    engine: str
    text: str
    blocks: list[OCRBlock] = field(default_factory=list)
    raw: dict | None = None  # engine's raw response, for debugging

    def to_dict(self):
        return {
            "page_num": self.page_num,
            "engine": self.engine,
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class FlaggedLine:
    line_index: int
    primary_text: str
    fallback_text: str
    similarity: float


@dataclass
class CrossCheckResult:
    page_num: int
    primary_engine: str
    fallback_engine: str
    agreement_ratio: float
    flagged_lines: list[FlaggedLine] = field(default_factory=list)

    def to_dict(self):
        return {
            "page_num": self.page_num,
            "primary_engine": self.primary_engine,
            "fallback_engine": self.fallback_engine,
            "agreement_ratio": self.agreement_ratio,
            "flagged_lines": [asdict(f) for f in self.flagged_lines],
        }


@dataclass
class StructuredSection:
    layer: str  # e.g. "mūla", "gādādharī", "bāladevī", "vimalaprabhā", "footnote"
    text: str


@dataclass
class StructuredPage:
    pdf_page: int
    printed_page: str | None
    header: str | None
    sections: list[StructuredSection]
    needs_review: bool
    review_notes: list[str] = field(default_factory=list)
    source_engine: str = ""

    def to_dict(self):
        return {
            "pdf_page": self.pdf_page,
            "printed_page": self.printed_page,
            "header": self.header,
            "sections": [asdict(s) for s in self.sections],
            "needs_review": self.needs_review,
            "review_notes": self.review_notes,
            "source_engine": self.source_engine,
        }
