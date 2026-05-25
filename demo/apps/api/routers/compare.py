"""B0 / B1 / A side-by-side + amortization curve — Phase 4 thesis-proving."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad import compare as compare_service

from openacad.runtime import llm as llm

from openacad.runtime import db
router = APIRouter()


class CompareRequest(BaseModel):
    question: str
    paper_ids: list[str]


@router.post("")
def compare(req: CompareRequest) -> dict:
    if not llm.have_api_key():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no LLM API key configured")
    out = compare_service.compare_one(req.question, req.paper_ids)
    return {k: v.model_dump(mode="json") for k, v in out.items()}


class CurveRequest(BaseModel):
    paper_ids: list[str]
    questions: list[str]


@router.post("/curve")
def amortization_curve(req: CurveRequest) -> dict:
    if not llm.have_api_key():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no LLM API key configured")
    return compare_service.amortization_curve(req.questions, req.paper_ids)


@router.get("/history")
def history(pipeline: str | None = None) -> list[dict]:
    results = db.list_comparisons()
    if pipeline:
        results = [r for r in results if r.pipeline == pipeline]
    return [r.model_dump(mode="json") for r in results]
