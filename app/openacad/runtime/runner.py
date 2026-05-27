"""Agent runner — loads agent + skill specs from the vault and runs via PydanticAI.

Wires:
  - agent spec (.md frontmatter + body)
  - referenced skills (their tools + instructions get folded in)
  - tool registry (name → callable)
  - PydanticAI Agent (model + system prompt + tools)
  - vault dependency (bound into each tool via a signature-rewriting closure)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from openacad.runtime.agent_spec import AgentSpec
from openacad.runtime.loader import load_agents, load_skills
from openacad.runtime.skill_spec import SkillSpec
from openacad.runtime.tool_registry import ToolRegistry, get_registry

if TYPE_CHECKING:
    from openacad.vault import Vault


@dataclass
class RunResult:
    """Result of an AgentRunner.run() call."""

    agent: str
    output: Any
    instruction: str
    tools_used: list[str]
    raw: Any = None


class AgentRunner:
    """Loads agent + skill specs from a vault, resolves tools, executes via PydanticAI."""

    def __init__(self, vault: "Vault | None") -> None:
        self.vault = vault
        self.tools: ToolRegistry = get_registry()
        self.agents: dict[str, AgentSpec] = load_agents(vault)
        self.skills: dict[str, SkillSpec] = load_skills(vault)

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, agent_name: str, *, user_prompt: str | None = None, **kwargs: Any) -> RunResult:
        """Run the named agent.

        - `user_prompt`: the user message. If omitted, falls back to a JSON dump of kwargs
          so callers can pass structured inputs (chunk_text, doc_id, ...).
        - `**kwargs`: forwarded into the user prompt as a JSON payload when `user_prompt`
          is not supplied. Also includes `question=...` for the answerer convention.
        """
        if agent_name not in self.agents:
            raise KeyError(f"agent {agent_name!r} not loaded; available: {sorted(self.agents)}")

        spec = self.agents[agent_name]
        instruction = self._compose_instruction(spec)
        tool_names, tool_callables = self._resolve_tools(spec)

        # Build the user prompt.
        if user_prompt is None:
            if "question" in kwargs:
                user_prompt = str(kwargs.pop("question"))
                if kwargs:
                    user_prompt = (
                        f"{user_prompt}\n\nAdditional context:\n{json.dumps(kwargs, default=str)}"
                    )
            elif kwargs:
                user_prompt = json.dumps(kwargs, default=str, indent=2)
            else:
                user_prompt = ""

        agent = self._build_pydantic_agent(spec, instruction, tool_callables)

        # Best-effort logging. The vault's activity log is part of M1; we tolerate its absence.
        self._log_activity(agent_name, spec, tool_names, user_prompt)

        result = agent.run_sync(user_prompt)
        output = getattr(result, "output", None)
        if output is None:
            output = getattr(result, "data", result)

        return RunResult(
            agent=agent_name,
            output=output,
            instruction=instruction,
            tools_used=tool_names,
            raw=result,
        )

    # ── plumbing ──────────────────────────────────────────────────────────────

    def _compose_instruction(self, spec: AgentSpec) -> str:
        """Concatenate the agent's instruction with any referenced skill instructions."""
        parts: list[str] = [spec.instruction.strip()]
        for skill_name in spec.skills:
            skill = self.skills.get(skill_name)
            if skill is None:
                continue
            block = skill.instruction.strip()
            if block:
                parts.append(f"## Skill: {skill.name}\n\n{block}")
        return "\n\n".join(p for p in parts if p)

    def _resolve_tools(self, spec: AgentSpec) -> tuple[list[str], list[Any]]:
        """Resolve agent + skill tools to callables, binding `vault` via a closure."""
        names: list[str] = []
        for t in spec.tools:
            if t not in names:
                names.append(t)
        for skill_name in spec.skills:
            skill = self.skills.get(skill_name)
            if skill is None:
                continue
            for t in skill.tools:
                if t not in names:
                    names.append(t)

        callables: list[Any] = []
        for name in names:
            if not self.tools.has(name):
                raise KeyError(
                    f"tool {name!r} referenced by agent {spec.name!r} is not registered"
                )
            fn = self.tools.resolve(name)
            bound = self._bind_vault(fn, name)
            callables.append(bound)
        return names, callables

    def _bind_vault(self, fn: Any, name: str) -> Any:
        """Bind `vault=self.vault` into the tool function so PydanticAI never sees it.

        We rebuild the signature without the `vault` parameter and produce a closure
        that calls the original with `vault=self.vault` injected. We deliberately do
        NOT set `__wrapped__` — that would make `inspect.signature` follow through to
        the unwrapped function and re-expose `vault` to the LLM-facing schema.
        """
        import inspect

        original_sig = inspect.signature(fn)
        params_without_vault = [
            p for name_, p in original_sig.parameters.items() if name_ != "vault"
        ]
        new_sig = original_sig.replace(parameters=params_without_vault)
        vault = self.vault

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, vault=vault, **kwargs)

        wrapper.__name__ = name
        wrapper.__doc__ = fn.__doc__
        wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
        # Preserve annotations minus `vault` so type-hint reflection still works.
        wrapper.__annotations__ = {
            k: v for k, v in getattr(fn, "__annotations__", {}).items() if k != "vault"
        }
        return wrapper

    def _build_pydantic_agent(
        self, spec: AgentSpec, instruction: str, tool_callables: list[Any]
    ) -> Any:
        """Construct the pydantic_ai.Agent for this spec.

        Isolated so tests can stub it out via monkeypatching.
        """
        from pydantic_ai import Agent

        return Agent(
            model=spec.model,
            system_prompt=instruction,
            tools=tool_callables,
        )

    def _log_activity(
        self, agent_name: str, spec: AgentSpec, tools: list[str], user_prompt: str
    ) -> None:
        """Append a JSON line to <vault>/.openacad/activity.jsonl. Best-effort."""
        if self.vault is None:
            return
        base = getattr(self.vault, "path", None) or getattr(self.vault, "root", None)
        if base is None:
            return
        try:
            from pathlib import Path

            log = Path(base) / ".openacad" / "activity.jsonl"
            log.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": datetime.now(UTC).isoformat(),
                "event": "agent_run",
                "agent": agent_name,
                "model": spec.model,
                "tools": tools,
                "prompt_preview": user_prompt[:200],
            }
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            # Logging must never fail an agent run.
            pass
