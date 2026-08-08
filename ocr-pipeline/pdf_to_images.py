import subprocess
from pathlib import Path

import config


def pdf_to_page_images(
    pdf_path: Path, out_dir: Path, first_page: int, last_page: int, dpi: int = None
) -> list[Path]:
    """Render pdf_path's [first_page, last_page] (1-indexed, inclusive) to PNGs
    at `out_dir/page-XXX.png`. Uses pdftoppm (poppler) since it's already the
    working tool in this project — no extra Python PDF dependency needed."""

    dpi = dpi or config.PDF_RENDER_DPI
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"

    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        "-f", str(first_page),
        "-l", str(last_page),
        str(pdf_path),
        str(prefix),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return sorted(out_dir.glob("page-*.png"))


def page_num_from_filename(path: Path) -> int:
    # pdftoppm names files page-NNN.png (zero-padded width depends on total pages)
    return int(path.stem.split("-")[-1])
