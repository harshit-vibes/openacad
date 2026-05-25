"""Q&A via tool-calling synthesis agent — Phase 3."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.feedback.schema import EvalEvent

from openacad.runtime.queries import SynthesisResult
from openacad.runtime import llm as llm
from openacad.agents.synthesizer import agent as synthesis_agent
from openacad.runtime import db
router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    paper_ids: list[str] | None = None


@router.post("", response_model=SynthesisResult)
def ask(req: QueryRequest) -> SynthesisResult:
    if not llm.have_api_key():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "no LLM API key configured — set ANTHROPIC_API_KEY / OPENAI_API_KEY",
        )
    return synthesis_agent.ask(req.question, paper_ids=req.paper_ids)


class MarkPoorRequest(BaseModel):
    answer_id: str
    expected_atoms: list[str] = []
    reason: str = ""


@router.post("/mark-poor")
def mark_poor(req: MarkPoorRequest) -> dict:
    """Feed the retrieval-tuning eval loop (Phase 4)."""
    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            kind="query_marked_poor",
            payload={
                "answer_id": req.answer_id,
                "expected_atoms": req.expected_atoms,
                "reason": req.reason,
            },
        )
    )
    return {"ok": True}
