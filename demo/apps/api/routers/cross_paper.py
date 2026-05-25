"""Cross-paper bridging — Phase 4."""

from typing import Any

from fastapi import APIRouter

from openacad import cross_paper as cross_paper_service

router = APIRouter()


@router.get("")
def find_cross_paper(
    source_a: str,
    source_b: str | None = None,
    min_shared_attributes: int = 1,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Atom pairs connecting paper A to paper B (direct edges + shared attributes)."""
    return cross_paper_service.find_cross_paper(
        source_a=source_a,
        source_b=source_b,
        min_shared_attributes=min_shared_attributes,
        limit=limit,
    )
