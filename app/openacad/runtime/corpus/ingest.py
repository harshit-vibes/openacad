"""High-level orchestrator: pdf → chunks → embeddings → persisted in SQLite.

Used by both routers/sources.py and the CLI ingest command, so they share one path.
"""

import re
from datetime import datetime
from pathlib import Path

from openacad.runtime.corpus.source import PaperSource
from openacad.runtime.corpus import pdf as pdf_service
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.runtime.corpus.chunking import chunk_pages


def _slugify(stem: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return s[:64] or "paper"


def make_source_id(pdf_path: Path) -> str:
    return f"paper-{_slugify(pdf_path.stem)}"


def ingest_pdf(pdf_path: Path) -> PaperSource:
    """Parse, chunk, embed (chunks only), persist source + chunks. Idempotent on id."""
    pdf_path = pdf_path.expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    source_id = make_source_id(pdf_path)
    pages, n_pages = pdf_service.extract_pages(pdf_path)
    title = pdf_service.extract_title(pdf_path)

    chunks = chunk_pages(pages, source_id=source_id)

    source = PaperSource(
        id=source_id,
        filename=pdf_path.name,
        title=title,
        uploaded_at=datetime.utcnow(),
        n_pages=n_pages,
        n_chunks=len(chunks),
    )
    db.upsert_source(source)
    db.upsert_chunks(chunks)

    # Embed chunks for the B1 baseline. Atom embeddings are written when atoms are accepted.
    semantic_service.chunks_store().upsert_many([(c.id, c.text) for c in chunks])

    return source
