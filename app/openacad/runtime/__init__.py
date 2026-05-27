"""openacad agent runtime over PydanticAI.

Public exports:
- AgentRunner: load + execute agents from a vault's `.openacad/agents/` sidecar
- AgentSpec / SkillSpec: pydantic models for the Claude Code `.md` formats
- ToolRegistry / @tool: name → callable mapping for shipped + user tools
"""

from openacad.runtime.agent_spec import AgentSpec
from openacad.runtime.runner import AgentRunner, RunResult
from openacad.runtime.skill_spec import SkillSpec
from openacad.runtime.tool_registry import REGISTRY, ToolRegistry, get_registry, tool

__all__ = [
    "AgentRunner",
    "AgentSpec",
    "SkillSpec",
    "RunResult",
    "ToolRegistry",
    "tool",
    "get_registry",
    "REGISTRY",
]
