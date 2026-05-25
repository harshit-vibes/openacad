"""Eval log + 4 loops + prompt promotion — Phase 4."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.feedback.schema import EvalEvent, PromptVersion
from openacad import eval_report as eval_service
from openacad.runtime import db
router = APIRouter()


@router.get("/events", response_model=list[EvalEvent])
def list_events(kind: str | None = None, limit: int = 100) -> list[EvalEvent]:
    return db.list_events(kind=kind, limit=limit)


@router.get("/metrics")
def metrics(prompt_version: str | None = None) -> dict:
    return eval_service.metrics(prompt_version)


@router.get("/prompts", response_model=list[PromptVersion])
def list_prompts(name: str | None = None) -> list[PromptVersion]:
    return eval_service.list_prompts(name)


class PromotePromptRequest(BaseModel):
    version: str


@router.post("/prompts/promote")
def promote_prompt(req: PromotePromptRequest) -> dict:
    try:
        return eval_service.promote_prompt(req.version)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.post("/regenerate")
def regenerate_prompt(name: str = "extraction") -> dict:
    if name != "extraction":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, f"regenerate for name={name}")
    pv = eval_service.regenerate_extraction_prompt()
    if pv is None:
        return {"ok": False, "reason": f"need at least {db.list_events.__defaults__ or ''} curate events to regenerate"}
    return {"ok": True, "version": pv.version, "state": pv.state}


@router.get("/loop2")
def loop2_retrieval_signal() -> dict:
    """Inspect the retrieval-tuning signal (poor-answer marks)."""
    return eval_service.review_retrieval_signal()


@router.get("/loop3")
def loop3_constraint_review() -> dict:
    """Inspect the registry-constraint-tightening signal (rejection patterns)."""
    return eval_service.review_registry_constraints()
