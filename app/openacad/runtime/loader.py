"""Load agent + skill specs from a vault's `.openacad/` sidecar, with package-data fallback.

Lookup order:
  1. `<vault.path>/.openacad/agents/*.md` (or `.../skills/*/SKILL.md`)
  2. Shipped defaults under `openacad/agents/*.md` and `openacad/skills/*/SKILL.md`,
     read via `importlib.resources`.

`load_agents(None)` and `load_skills(None)` return ONLY the shipped defaults —
useful for tests, CLI introspection, and `openacad agents list` when no vault is
in scope.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openacad.runtime.agent_spec import AgentSpec
from openacad.runtime.skill_spec import SkillSpec

if TYPE_CHECKING:
    from openacad.vault import Vault


def _vault_sidecar(vault: Any) -> Path | None:
    """Return <vault.path>/.openacad or None if vault is None or has no path."""
    if vault is None:
        return None
    base = getattr(vault, "path", None) or getattr(vault, "root", None)
    if base is None:
        return None
    side = Path(base) / ".openacad"
    return side if side.exists() else None


def _shipped_agents_root() -> Path:
    """Locate the shipped `openacad/agents/` directory on disk."""
    # importlib.resources.files() returns a Traversable; for an installed
    # package this might be a zip path, but in our editable install it's a
    # real filesystem path. We use Path() to normalise.
    return Path(str(resources.files("openacad.agents")))


def _shipped_skills_root() -> Path:
    return Path(str(resources.files("openacad.skills")))


def load_agents(vault: "Vault | None") -> dict[str, AgentSpec]:
    """Load all agent specs visible to this vault.

    Vault sidecar agents take precedence over shipped defaults of the same name.
    Pass `None` to load only shipped defaults (useful for CLI / tests).
    """
    specs: dict[str, AgentSpec] = {}

    # 1. Shipped defaults first.
    shipped = _shipped_agents_root()
    if shipped.exists():
        for path in sorted(shipped.glob("*.md")):
            try:
                spec = AgentSpec.from_markdown(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if spec.name:
                specs[spec.name] = spec

    # 2. Vault sidecar overrides.
    side = _vault_sidecar(vault)
    if side is not None:
        agents_dir = side / "agents"
        if agents_dir.exists():
            for path in sorted(agents_dir.glob("*.md")):
                try:
                    spec = AgentSpec.from_markdown(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if spec.name:
                    specs[spec.name] = spec

    return specs


def load_skills(vault: "Vault | None") -> dict[str, SkillSpec]:
    """Load all skill specs visible to this vault.

    Vault sidecar skills override shipped ones with the same name.
    """
    specs: dict[str, SkillSpec] = {}

    # 1. Shipped defaults.
    shipped = _shipped_skills_root()
    if shipped.exists():
        for skill_dir in sorted(shipped.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                spec = SkillSpec.from_markdown(skill_md.read_text(encoding="utf-8"))
            except Exception:
                continue
            if spec.name:
                specs[spec.name] = spec

    # 2. Vault sidecar overrides.
    side = _vault_sidecar(vault)
    if side is not None:
        skills_dir = side / "skills"
        if skills_dir.exists():
            for skill_dir in sorted(skills_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                try:
                    spec = SkillSpec.from_markdown(skill_md.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if spec.name:
                    specs[spec.name] = spec

    return specs
