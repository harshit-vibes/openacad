"""Three-stage extraction pipeline — Phase 2."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.notes.schema import DraftAtom
from openacad.notes.intake import from_chunks as extraction_pipeline
from openacad.runtime import llm as llm
from openacad.runtime import db
router = APIRouter()


class ExtractRequest(BaseModel):
    source_id: str
    chunk_ids: list[str] | None = None


class DraftIds(BaseModel):
    draft_ids: list[str]


@router.post("/draft", response_model=list[DraftAtom])
def draft_atoms(req: ExtractRequest) -> list[DraftAtom]:
    """Stage 1: run extraction agent → persist DraftAtoms."""
    if not llm.have_api_key():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"LLM_PROVIDER={req.source_id and 'configured'} but no API key set. "
            "Set the *_API_KEY env var matching LLM_PROVIDER.",
        )
    if not db.get_source(req.source_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"source {req.source_id} not found")
    return extraction_pipeline.draft(req.source_id, chunk_ids=req.chunk_ids)


@router.post("/validate")
def validate_drafts(req: DraftIds) -> dict[str, list[str]]:
    """Stage 2: registry strict-validate each draft. Returns {draft_id: [error...]}"""
    return extraction_pipeline.validate(req.draft_ids)


@router.post("/score")
def score_drafts(req: DraftIds) -> dict[str, float]:
    """Stage 3: confidence + duplicate-similarity score for each draft."""
    return extraction_pipeline.score(req.draft_ids)


@router.get("/drafts/{source_id}", response_model=list[DraftAtom])
def list_drafts(source_id: str) -> list[DraftAtom]:
    """Drafts pending HITL review for a source."""
    if not db.get_source(source_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, source_id)
    return db.drafts_for_source(source_id)
