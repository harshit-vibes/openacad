"""Graph-mining for contradictions — Phase 4."""

from typing import Any

from fastapi import APIRouter

from openacad import contradictions as contradiction_service

router = APIRouter()


@router.get("")
def find_contradictions(
    type: str | None = None,
    domain: str | None = None,
    include_weak: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return contradicting atom pairs (strong + optional weak)."""
    return contradiction_service.find_contradictions(
        type=type, domain=domain, include_weak=include_weak, limit=limit
    )
