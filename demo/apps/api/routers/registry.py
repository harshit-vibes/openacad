"""Registry catalogs + proposal queue + manual promotion — Phase 2."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from openacad.notes.registry.schema import AttributeDef, Proposal, RelationDef, TypeDef
from openacad.notes.registry import _legacy as registry_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.notes.registry.validation import get_schema

router = APIRouter()


@router.get("/attributes", response_model=list[AttributeDef])
def list_attributes() -> list[AttributeDef]:
    return list(get_schema().attributes.values())


@router.get("/attributes/{key}", response_model=AttributeDef)
def get_attribute(key: str) -> AttributeDef:
    ad = get_schema().get_attribute(key)
    if not ad:
        raise HTTPException(status.HTTP_404_NOT_FOUND, key)
    return ad


@router.get("/relations", response_model=list[RelationDef])
def list_relations() -> list[RelationDef]:
    return list(get_schema().relations.values())


@router.get("/relations/{key}", response_model=RelationDef)
def get_relation(key: str) -> RelationDef:
    rd = get_schema().get_relation(key)
    if not rd:
        raise HTTPException(status.HTTP_404_NOT_FOUND, key)
    return rd


@router.get("/types", response_model=list[TypeDef])
def list_types() -> list[TypeDef]:
    return list(get_schema().types.values())


@router.get("/proposals", response_model=list[Proposal])
def list_proposals(state: str | None = None) -> list[Proposal]:
    return db.list_proposals(state)


class PromoteRequest(BaseModel):
    proposal_id: str
    payload: dict | None = None


@router.post("/proposals/promote")
def promote_proposal(req: PromoteRequest) -> dict:
    try:
        return registry_service.promote_proposal(req.proposal_id, req.payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except NotImplementedError as e:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(e)) from e


class RejectProposalRequest(BaseModel):
    proposal_id: str


@router.post("/proposals/reject")
def reject_proposal(req: RejectProposalRequest) -> dict:
    try:
        return registry_service.reject_proposal(req.proposal_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.get("/schema-evolution")
def schema_evolution_log() -> dict:
    path = vault_io.schema_evolution_path()
    if not path.exists():
        return {"path": str(path), "entries": ""}
    return {"path": str(path), "entries": path.read_text(encoding="utf-8")}


@router.post("/recount")
def recount() -> dict:
    """Force a usage-recount sweep + auto-promotion check."""
    return registry_service.recount_usage_and_promote()
