"""PyMuPDF text extraction with per-page character offset tracking."""

from pathlib import Path
from typing import TypedDict

import pymupdf


class PageRecord(TypedDict):
    ordinal: int       # 1-indexed page number
    text: str
    char_start: int    # cumulative char offset into the concatenated document text


def extract_pages(pdf_path: Path) -> tuple[list[PageRecord], int]:
    """Open the PDF, extract per-page text, return (pages, n_pages).

    Each page record carries the absolute char offset so chunking can
    reconstruct page_range for any char span.
    """
    doc = pymupdf.open(str(pdf_path))
    pages: list[PageRecord] = []
    char_offset = 0
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"ordinal": i + 1, "text": text, "char_start": char_offset})
        char_offset += len(text)
    n_pages = doc.page_count
    doc.close()
    return pages, n_pages


def extract_title(pdf_path: Path) -> str | None:
    """Best-effort title extraction from PDF metadata, fallback to filename stem."""
    doc = pymupdf.open(str(pdf_path))
    title = (doc.metadata or {}).get("title") or None
    doc.close()
    if title and title.strip():
        return title.strip()
    return pdf_path.stem
