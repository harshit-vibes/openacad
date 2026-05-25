"""PaperSource ingestion and listing — Phase 1c."""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from openacad.runtime.settings import settings
from openacad.runtime.corpus.source import Chunk, PaperSource
from openacad.runtime.corpus import ingest as ingest_service
from openacad.runtime import db
router = APIRouter()


@router.get("", response_model=list[PaperSource])
def list_sources() -> list[PaperSource]:
    return db.list_sources()


@router.post("", response_model=PaperSource)
async def upload_source(file: UploadFile) -> PaperSource:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "PDF only")

    sources_dir = settings.data_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    dest = sources_dir / file.filename

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        shutil.move(str(tmp_path), str(dest))
        return ingest_service.ingest_pdf(dest)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e)) from e


@router.get("/{source_id}", response_model=PaperSource)
def get_source(source_id: str) -> PaperSource:
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, source_id)
    return source


@router.get("/{source_id}/chunks", response_model=list[Chunk])
def get_source_chunks(source_id: str) -> list[Chunk]:
    if not db.get_source(source_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, source_id)
    return db.chunks_for_source(source_id)


@router.get("/{source_id}/text")
def get_source_text(source_id: str) -> dict:
    if not db.get_source(source_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, source_id)
    chunks = db.chunks_for_source(source_id)
    return {
        "source_id": source_id,
        "n_chunks": len(chunks),
        "text": "\n\n".join(c.text for c in chunks),
    }
