"""Longer-form synthesis — topic to paragraph draft with citations — Phase 4."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.runtime.queries import SynthesisResult
from openacad.runtime import llm as llm
from openacad import synthesis as synthesis_service

router = APIRouter()


class SynthesizeRequest(BaseModel):
    topic: str | None = None
    atom_ids: list[str] | None = None
    style: str = "academic"
    max_words: int = 400


@router.post("", response_model=SynthesisResult)
def synthesize(req: SynthesizeRequest) -> SynthesisResult:
    if not llm.have_api_key():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no LLM API key configured")
    if not req.topic and not req.atom_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "provide topic and/or atom_ids")
    return synthesis_service.synthesize(
        topic=req.topic,
        atom_ids=req.atom_ids,
        style=req.style,
        max_words=req.max_words,
    )
