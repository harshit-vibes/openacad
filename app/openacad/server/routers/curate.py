"""HITL curate actions — Phase 2."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.notes.schema import AtomicNote, DraftAtom
from openacad.notes.curation import _legacy as curate_service
router = APIRouter()


class AcceptRequest(BaseModel):
    draft_id: str


class EditRequest(BaseModel):
    edited: DraftAtom


class RejectRequest(BaseModel):
    draft_id: str
    reason: str


@router.post("/accept", response_model=AtomicNote)
def accept_draft(req: AcceptRequest) -> AtomicNote:
    try:
        return curate_service.accept(req.draft_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.post("/edit", response_model=AtomicNote)
def edit_draft(req: EditRequest) -> AtomicNote:
    try:
        return curate_service.edit_and_accept(req.edited)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.post("/reject")
def reject_draft(req: RejectRequest) -> dict:
    try:
        return curate_service.reject(req.draft_id, req.reason)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
