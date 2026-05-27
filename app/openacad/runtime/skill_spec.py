"""Skill spec — the Claude Code `SKILL.md` skill format.

A skill is a reusable bundle of tools + instructions + optional sub-agents that
any agent can reference in its `skills:` frontmatter. The runner injects the
skill's instructions into the agent's effective system prompt and unions the
skill's tools into the agent's toolset.
"""

from __future__ import annotations

import frontmatter
from pydantic import BaseModel, Field


class SkillSpec(BaseModel):
    """One skill loaded from a `.claude/skills/<name>/SKILL.md`-style file."""

    name: str
    description: str = ""
    tools: list[str] = Field(default_factory=list)
    sub_agents: list[str] = Field(default_factory=list)
    instruction: str = ""

    @classmethod
    def from_markdown(cls, text: str) -> SkillSpec:
        """Parse a Claude Code SKILL.md (frontmatter + body)."""
        post = frontmatter.loads(text)
        meta = dict(post.metadata)
        return cls(
            name=str(meta.get("name", "")),
            description=str(meta.get("description", "")),
            tools=[str(t) for t in (meta.get("tools") or [])],
            sub_agents=[str(s) for s in (meta.get("sub_agents") or [])],
            instruction=post.content.strip(),
        )

    def to_markdown(self) -> str:
        """Serialize back to a `.md` file body."""
        post = frontmatter.Post(
            self.instruction,
            **{
                "name": self.name,
                "description": self.description,
                "tools": list(self.tools),
                "sub_agents": list(self.sub_agents),
            },
        )
        return frontmatter.dumps(post)
