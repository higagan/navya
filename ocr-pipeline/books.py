"""Per-book structure: which commentary layers a volume contains, and how
they are laid out on the page.

This exists because the layer vocabulary was previously hardcoded in the
LLM prompt — and the names there belonged to a different volume, so the
model reported a Bāladevī section in a book that has none and never
labelled the Dīdhiti that is actually present. Layer names are a property
of the book, not of the pipeline.

Everything below for Avayavaprakaraṇam comes from the domain expert
labelling real blocks on printed pages ३ and ४, not from inference.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Layer:
    name: str  # Devanagari, as the expert named it
    roman: str
    hint: str = ""
    # Commentary depth: 0 is the text being glossed, 1 comments on 0, 2 on 1.
    # A passage may only gloss a strictly shallower layer — गादाधरी explains
    # the दीधिति, never its own sub-commentary. None means "page furniture",
    # which neither glosses nor is glossed.
    depth: int | None = None


@dataclass(frozen=True)
class Book:
    slug: str
    title: str
    edition: str
    layers: tuple[Layer, ...]
    layout_note: str = ""
    expert_labelled: dict[int, tuple[str, ...]] = field(default_factory=dict)

    @property
    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]

    @property
    def depths(self) -> dict[str, int | None]:
        return {layer.name: layer.depth for layer in self.layers}

    def prompt_block(self) -> str:
        """The layer vocabulary and layout evidence, as given to the model."""
        lines = ["KNOWN LAYERS for this book (use only these names):"]
        for layer in self.layers:
            desc = f"- {layer.name} ({layer.roman})"
            if layer.hint:
                desc += f" — {layer.hint}"
            lines.append(desc)
        if self.layout_note:
            lines += ["", f"LAYOUT: {self.layout_note}"]
        return "\n".join(lines)


AVAYAVAPRAKARANAM = Book(
    slug="avayavaprakaranam",
    title="Avayavaprakaraṇam (Anumāna Gādādharī)",
    edition="ed. Jvālāprasād Gauḍ with the Vilāsinī commentary, Varanasi, 1964",
    layers=(
        Layer(
            "शीर्षक", "header", "running head and page number, one short line at the very top"
        ),  # depth None
        Layer(
            "दीधिति",
            "dīdhiti",
            "the text being glossed. Short — often only a few lines — and sometimes "
            "set in smaller type. Reads as continuous prose rather than opening by "
            "quoting a word",
            depth=0,
        ),
        Layer(
            "गादाधरी",
            "gādādharī",
            "the main commentary and the bulk of the volume. Typically opens by "
            "quoting a word from the दीधिति followed by इति, then glossing it",
            depth=1,
        ),
        Layer(
            "विलासिनी",
            "vilāsinī",
            "the editor's sub-commentary, below the गादाधरी. Also glosses word by "
            "word, and may refer back to the root explicitly (e.g. opening मूले)",
            depth=2,
        ),
        Layer("टिप्पणी", "footnote", "foot of the page, opening with a Devanagari numeral"),
        Layer("मूल", "mūla", "the root text itself. Rare — only a few lines, often absent", depth=0),
    ),
    layout_note=(
        "Blocks run top to bottom in that order, though a page may omit any of "
        "them — a continuation page often begins straight into गादाधरी. Position "
        "on the page is the strongest signal; do not assign a layer on subject "
        "matter alone.\n"
        "Keep a short block between the शीर्षक and the first long commentary as "
        "its own section — that is the दीधिति (or मूल) being glossed, and it is "
        "separated from what follows by a horizontal rule. Do not merge it into "
        "the गादाधरी just because it is brief.\n"
        "Where two long commentary blocks follow one another, the upper is "
        "गादाधरी and the lower is विलासिनी. Do not label both the same."
    ),
    # Ground truth from the expert, kept for scoring changes to the pipeline.
    expert_labelled={
        17: ("शीर्षक", "दीधिति", "गादाधरी", "विलासिनी"),
        18: ("गादाधरी", "विलासिनी", "टिप्पणी"),
    },
)

BOOKS: dict[str, Book] = {AVAYAVAPRAKARANAM.slug: AVAYAVAPRAKARANAM}


def get(slug: str) -> Book | None:
    return BOOKS.get(slug)
