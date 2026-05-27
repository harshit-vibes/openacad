"""Agent-spec API routes for the Next.js playground.

Endpoints:

- ``GET /agents``                       list shipped + vault-customised agents
- ``GET /agents/{name}``                full agent spec (frontmatter + body)
- ``GET /agents/{name}/diff``           diff vs ``.openacad/agents/proposed/``
- ``GET /agents/{name}/versions``       list promoted version files
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from openacad.runtime.agent_spec import AgentSpec
from openacad.runtime.loader import load_agents
from openacad.server.deps import get_vault
from openacad.vault import Vault

router = APIRouter()


def _agent_to_dict(spec: AgentSpec, source: str) -> dict[str, Any]:
    return {
        "name": spec.name,
        "description": spec.description,
        "model": spec.model,
        "tools": list(spec.tools),
        "skills": list(spec.skills),
        "instruction": spec.instruction,
        "source": source,  # "shipped" | "vault" | "proposed"
    }


def _vault_agent_path(vault: Vault, name: str) -> Path:
    return vault.agents_dir / f"{name}.md"


def _proposed_agent_path(vault: Vault, name: str) -> Path:
    return vault.agents_dir / "proposed" / f"{name}.md"


@router.get("")
def list_agents_route(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """List agents visible to this vault (sidecar overrides shipped)."""
    specs = load_agents(vault)
    rows: list[dict[str, Any]] = []
    for name in sorted(specs):
        spec = specs[name]
        # Determine if it's shipped or vault-customised.
        vault_path = _vault_agent_path(vault, name)
        source = "vault" if vault_path.exists() else "shipped"
        has_proposed = _proposed_agent_path(vault, name).exists()
        rows.append({
            "name": spec.name,
            "description": spec.description,
            "model": spec.model,
            "tools": list(spec.tools),
            "skills": list(spec.skills),
            "source": source,
            "has_proposed": has_proposed,
        })
    return {"agents": rows, "count": len(rows)}


@router.get("/{name}")
def get_agent(name: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    specs = load_agents(vault)
    spec = specs.get(name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"agent {name!r} not found")

    vault_path = _vault_agent_path(vault, name)
    source = "vault" if vault_path.exists() else "shipped"

    proposed_path = _proposed_agent_path(vault, name)
    proposed: dict[str, Any] | None = None
    if proposed_path.exists():
        try:
            proposed_spec = AgentSpec.from_markdown(proposed_path.read_text("utf-8"))
            proposed = _agent_to_dict(proposed_spec, "proposed")
        except Exception:  # noqa: BLE001
            proposed = None

    return {
        **_agent_to_dict(spec, source),
        "proposed": proposed,
        "vault_path": str(vault_path) if vault_path.exists() else None,
    }


@router.get("/{name}/diff")
def diff_agent(name: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Return a unified diff between the active agent .md and the proposed one."""
    specs = load_agents(vault)
    spec = specs.get(name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"agent {name!r} not found")

    proposed_path = _proposed_agent_path(vault, name)
    if not proposed_path.exists():
        return {
            "name": name,
            "has_proposed": False,
            "diff": "",
            "active": spec.to_markdown(),
            "proposed": None,
        }

    active_md = spec.to_markdown()
    proposed_md = proposed_path.read_text("utf-8")
    diff = "".join(
        difflib.unified_diff(
            active_md.splitlines(keepends=True),
            proposed_md.splitlines(keepends=True),
            fromfile=f"{name}.md (active)",
            tofile=f"{name}.md (proposed)",
        )
    )
    return {
        "name": name,
        "has_proposed": True,
        "diff": diff,
        "active": active_md,
        "proposed": proposed_md,
    }


@router.get("/{name}/versions")
def agent_versions(name: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """List promoted version files in ``.openacad/agents/versions/<name>/``."""
    versions_dir = vault.agents_dir / "versions" / name
    if not versions_dir.exists():
        return {"name": name, "versions": []}
    versions = sorted(versions_dir.glob("*.md"))
    return {
        "name": name,
        "versions": [
            {"file": p.name, "modified_at": p.stat().st_mtime}
            for p in versions
        ],
    }
