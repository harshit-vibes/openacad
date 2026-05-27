"""Tool registry behavior: register, resolve, names, schema-correctness signal."""

from __future__ import annotations

import pytest

from openacad.runtime.tool_registry import REGISTRY, ToolRegistry, get_registry, tool


def test_register_and_resolve() -> None:
    reg = ToolRegistry()

    def add(a: int, b: int) -> int:
        """Add two ints."""
        return a + b

    reg.register("add", add)
    assert reg.has("add")
    assert reg.resolve("add") is add
    assert "add" in reg
    assert reg.names() == ["add"]


def test_resolve_missing_raises_key_error() -> None:
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.resolve("nope")


def test_register_same_callable_is_idempotent() -> None:
    reg = ToolRegistry()

    def t() -> None: ...

    reg.register("t", t)
    reg.register("t", t)  # should not raise
    assert reg.resolve("t") is t


def test_register_conflict_raises() -> None:
    reg = ToolRegistry()

    def a() -> None: ...

    def b() -> None: ...

    reg.register("x", a)
    with pytest.raises(ValueError):
        reg.register("x", b)


def test_at_tool_decorator_registers_global() -> None:
    @tool
    def _unique_test_tool(x: int = 1) -> int:
        """Sample tool."""
        return x

    assert REGISTRY.has("_unique_test_tool")
    assert REGISTRY.resolve("_unique_test_tool") is _unique_test_tool


def test_get_registry_triggers_tool_import() -> None:
    """Calling get_registry() must import openacad.tools so the 10 shipped tools register."""
    reg = get_registry()
    for name in [
        "search_vault",
        "semantic_search",
        "traverse_relations",
        "incoming",
        "outgoing",
        "get_atom",
        "propose_atom",
        "check_contradiction",
        "read_chunk",
        "source_text",
    ]:
        assert reg.has(name), f"{name!r} not registered"


def test_resolved_tool_carries_docstring_and_annotations() -> None:
    """Schema reflection in PydanticAI needs docstring + annotations on the callable."""
    reg = get_registry()
    fn = reg.resolve("search_vault")
    assert fn.__doc__, "search_vault has no docstring"
    # Annotated[T, "desc"] on parameters is the contract.
    annotations = fn.__annotations__
    assert "query" in annotations
    assert "top_k" in annotations
