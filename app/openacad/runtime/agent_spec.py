"""Agent spec — the Claude Code `.md` agent format.

Frontmatter (`name`, `description`, `model`, `tools`, `skills`) + body (instruction).
Round-trips through markdown: `AgentSpec.from_markdown(text).to_markdown()` is lossless
modulo frontmatter key ordering.
"""

from __future__ import annotations

import frontmatter
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """One agent loaded from a `.claude/agents/<name>.md`-style file."""

    name: str
    description: str = ""
    model: str = "openai/gpt-4o-mini"
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    instruction: str = ""

    @classmethod
    def from_markdown(cls, text: str) -> AgentSpec:
        """Parse a Claude Code agent .md (frontmatter + body)."""
        post = frontmatter.loads(text)
        meta = dict(post.metadata)
        return cls(
            name=str(meta.get("name", "")),
            description=str(meta.get("description", "")),
            model=str(meta.get("model", "openai/gpt-4o-mini")),
            tools=[str(t) for t in (meta.get("tools") or [])],
            skills=[str(s) for s in (meta.get("skills") or [])],
            instruction=post.content.strip(),
        )

    def to_markdown(self) -> str:
        """Serialize back to a `.md` file body."""
        post = frontmatter.Post(
            self.instruction,
            **{
                "name": self.name,
                "description": self.description,
                "model": self.model,
                "tools": list(self.tools),
                "skills": list(self.skills),
            },
        )
        return frontmatter.dumps(post)
