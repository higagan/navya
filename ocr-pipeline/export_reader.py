"""Flatten the pipeline's output into what a reader needs.

The pipeline emits one record per page. A reader needs the opposite view:
addressable passages, each knowing what it glosses and what glosses it, and
each carrying the printed page it came from so any claim can be checked
against the scan.

Nothing here infers anything. It joins what the structuring step and the
pratīka linker already produced, and carries their uncertainty forward —
an unresolved quotation stays visible as unresolved rather than being
dropped, because a reader that hides what it couldn't work out is exactly
the thing this project exists to avoid.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pratika import link_document


@dataclass
class Passage:
    id: str  # e.g. "p20.s2" — stable, page + section index
    pdf_page: int
    printed_page: str | None
    layer: str
    text: str
    needs_review: bool = False
    review_notes: list[str] = field(default_factory=list)


@dataclass
class Gloss:
    """One commentary quoting one passage."""

    from_id: str  # the commenting passage
    to_id: str | None  # the passage being glossed, if it was found
    stem: str  # the words quoted
    from_offset: int  # where the quotation sits in the commenting passage
    to_offset: int | None  # where the quoted words sit in the glossed passage
    named_source: str | None = None  # layer the commentator named outright

    @property
    def resolved(self) -> bool:
        return self.to_id is not None


def _passage_id(pdf_page: int, section_index: int) -> str:
    return f"p{pdf_page}.s{section_index}"


def build(structured_jsonl: Path) -> dict:
    pages = [
        json.loads(line)
        for line in structured_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pages = [p for p in pages if p.get("sections")]

    passages: list[Passage] = []
    index: dict[tuple[int, str, int], str] = {}  # (pdf_page, layer, offset) -> id
    for page in pages:
        for i, sec in enumerate(page["sections"]):
            pid = _passage_id(page["pdf_page"], i)
            passages.append(
                Passage(
                    id=pid,
                    pdf_page=page["pdf_page"],
                    printed_page=page.get("printed_page"),
                    layer=sec["layer"],
                    text=sec["text"],
                    needs_review=page.get("needs_review", False),
                    review_notes=page.get("review_notes", []),
                )
            )
            index[(page["pdf_page"], sec["layer"], i)] = pid

    glosses: list[Gloss] = []
    for pdf_page, sections in link_document(pages).items():
        for sec_i, links in sections.items():
            from_id = _passage_id(pdf_page, sec_i)
            for link in links:
                # The linker reports which passage it matched, so there is no
                # reverse lookup to get wrong.
                to_id = _passage_id(*link.source_ref) if link.resolved and link.source_ref else None
                glosses.append(
                    Gloss(
                        from_id=from_id,
                        to_id=to_id,
                        stem=link.quotation.stem,
                        from_offset=link.quotation.offset,
                        to_offset=link.source_offset,
                        named_source=link.explicit_source,
                    )
                )

    resolved = sum(1 for g in glosses if g.resolved)
    return {
        "passages": [asdict(p) for p in passages],
        "glosses": [
            {k: v for k, v in asdict(g).items()} | {"resolved": g.resolved} for g in glosses
        ],
        "stats": {
            "pages": len(pages),
            "passages": len(passages),
            "quotations": len(glosses),
            "resolved": resolved,
        },
    }


if __name__ == "__main__":
    import sys

    src = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "output/jsonl/avayavaprakaranam/structured_pages.jsonl"
    )
    data = build(src)
    out = Path("output/reader_data.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out}: {data['stats']}")
