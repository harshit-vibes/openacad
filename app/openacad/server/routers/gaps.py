"""Weak-claim detector — Phase 4."""

from typing import Any

from fastapi import APIRouter

from openacad import gaps as gap_service

router = APIRouter()


@router.get("")
def find_gaps(
    confidence_threshold: str = "high",
    domain: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """High-confidence atoms with no supporting evidence."""
    return gap_service.find_gaps(
        confidence_threshold=confidence_threshold, domain=domain, limit=limit
    )
