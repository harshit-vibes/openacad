"""Sliding-window character chunker with word-boundary snapping and page tracking."""

from openacad.runtime.corpus.source import Chunk
from openacad.runtime.corpus.pdf import PageRecord

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def chunk_pages(
    pages: list[PageRecord],
    source_id: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Produce overlapping char-windowed chunks, tracking page_range and char_range.

    Snaps window ends to whitespace where possible so chunks don't slice mid-word.
    """
    full_text = "".join(p["text"] for p in pages)
    if not full_text:
        return []

    # Build a char→page index. For perf, page boundaries are sparse — use bisect.
    page_starts = [p["char_start"] for p in pages]
    page_ordinals = [p["ordinal"] for p in pages]

    def page_at(char_pos: int) -> int:
        # find rightmost page whose char_start <= char_pos
        lo, hi = 0, len(page_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if page_starts[mid] <= char_pos:
                lo = mid
            else:
                hi = mid - 1
        return page_ordinals[lo]

    chunks: list[Chunk] = []
    ordinal = 0
    i = 0
    n = len(full_text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            ws = full_text.rfind(" ", i + size // 2, end)
            if ws > i:
                end = ws

        text = full_text[i:end].strip()
        if text:
            chunks.append(
                Chunk(
                    id=f"c-{source_id}-{ordinal:04d}",
                    source_id=source_id,
                    ordinal=ordinal,
                    text=text,
                    page_range=(page_at(i), page_at(end - 1)),
                    char_range=(i, end),
                )
            )
            ordinal += 1

        if end >= n:
            break
        i = max(end - overlap, i + 1)

    return chunks
