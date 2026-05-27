"""Split a PDF into chunks.

Two modes:
  - fixed: every N pages → one part
  - chapters: explicit [(name, start_page, end_page), ...] mapping (1-indexed pages)

Used to turn a large source into demo-friendly bites.
"""

import sys
from pathlib import Path

import pymupdf

DEMO_ROOT = Path(__file__).resolve().parent.parent


def split_fixed(src: Path, pages_per_chunk: int = 5, out_dir: Path | None = None, prefix: str | None = None) -> list[Path]:
    src = src.expanduser().resolve()
    out_dir = (out_dir or DEMO_ROOT / "data" / "sources").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = prefix or src.stem.lower().replace(" ", "-").replace("_", "-")

    doc = pymupdf.open(str(src))
    n = doc.page_count
    paths: list[Path] = []
    part = 0
    for start in range(0, n, pages_per_chunk):
        end = min(start + pages_per_chunk - 1, n - 1)
        part += 1
        out_path = out_dir / f"{prefix}-part-{part:02d}.pdf"
        out_doc = pymupdf.open()
        out_doc.insert_pdf(doc, from_page=start, to_page=end)
        out_doc.save(str(out_path))
        out_doc.close()
        paths.append(out_path)
        print(f"  pages {start + 1}-{end + 1} → {out_path.name}")
    doc.close()
    return paths


def split_chapters(
    src: Path,
    chapters: list[tuple[str, int, int]],  # (slug, start_1indexed, end_1indexed)
    out_dir: Path | None = None,
    prefix: str | None = None,
) -> list[Path]:
    src = src.expanduser().resolve()
    out_dir = (out_dir or DEMO_ROOT / "data" / "sources").expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = prefix or src.stem.lower().replace(" ", "-").replace("_", "-")

    doc = pymupdf.open(str(src))
    paths: list[Path] = []
    for i, (slug, start, end) in enumerate(chapters, start=1):
        out_path = out_dir / f"{prefix}-ch{i:02d}-{slug}.pdf"
        out_doc = pymupdf.open()
        out_doc.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
        out_doc.save(str(out_path))
        out_doc.close()
        paths.append(out_path)
        print(f"  pages {start}-{end} ({end - start + 1}p) → {out_path.name}")
    doc.close()
    return paths


# Chapter map specific to the SDG Briefing 2023 PDF, derived from in-document headings.
SDG_CHAPTERS: list[tuple[str, int, int]] = [
    ("front-matter",        1,  4),   # cover, quote, TOC
    ("sdg-1-5-people",      5, 13),   # poverty/hunger/health/education/gender + impl
    ("sdg-6-10",           14, 20),   # water/energy/work/industry/inequality + impl
    ("sdg-11-15",          21, 28),   # cities/consumption/climate/oceans/land + impl
    ("sdg-16-17-peace",    29, 35),   # peace + partnerships + impl + closing
]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage:\n"
            "  python scripts/split_pdf.py <pdf>                  # uses SDG chapter map if filename matches\n"
            "  python scripts/split_pdf.py <pdf> --pages N        # fixed N-page chunks\n",
            file=sys.stderr,
        )
        sys.exit(1)

    src = Path(sys.argv[1])
    if "--pages" in sys.argv:
        n = int(sys.argv[sys.argv.index("--pages") + 1])
        paths = split_fixed(src, pages_per_chunk=n)
    elif "sdg" in src.stem.lower() or "briefing" in src.stem.lower():
        paths = split_chapters(src, SDG_CHAPTERS, prefix="sdg-briefing")
    else:
        paths = split_fixed(src, pages_per_chunk=5)
    print(f"wrote {len(paths)} parts to data/sources/")
