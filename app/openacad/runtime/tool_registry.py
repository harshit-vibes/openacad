"""Tool registry — name → callable mapping for agents.

Tools are plain Python functions decorated with `@tool`. The decorator registers
the function by name in a module-global registry; agents reference tools by name
in their `tools:` frontmatter. The runner resolves names → callables at run time
and hands them to PydanticAI, which derives the JSON schema from type hints +
docstring via its tool reflection.

Tools are expected to take a keyword-only `vault: Vault` parameter. The runner
binds the vault via `functools.partial` before passing the partial to PydanticAI,
so the LLM sees only the LLM-facing parameters.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ToolRegistry:
    """Global registry of tool functions, keyed by tool name."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a tool function by name. Raises if already registered with a different fn."""
        existing = self._tools.get(name)
        if existing is not None and existing is not fn:
            # Allow idempotent re-registration of the same callable (e.g. test re-imports).
            raise ValueError(f"tool {name!r} already registered to a different callable")
        self._tools[name] = fn

    def resolve(self, name: str) -> Callable[..., Any]:
        """Return the registered callable for `name`. Raises KeyError if missing."""
        try:
            return self._tools[name]
        except KeyError as e:
            raise KeyError(f"tool not registered: {name!r}") from e

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Module-global registry.
REGISTRY = ToolRegistry()


def tool(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: register `fn` in the global registry under its function name."""
    REGISTRY.register(fn.__name__, fn)
    return fn


def get_registry() -> ToolRegistry:
    """Return the module-global tool registry.

    Importing `openacad.tools` triggers the @tool decorators and populates this
    registry as a side effect.
    """
    # Trigger tool registration via side-effecting imports.
    import openacad.tools  # noqa: F401

    return REGISTRY
