"""MCP stdio server adapter for the openacad tool registry.

For each `@tool`-decorated function in `openacad.tools.*`, this module registers
an MCP tool whose:

- `name` mirrors the Python function name
- `description` comes from the docstring
- `inputSchema` is derived from the function's `Annotated[...]` type hints,
  skipping the keyword-only `vault: Vault` arg (the server injects the configured
  vault automatically)

When the MCP client calls a tool, we deserialize JSON args, invoke the function
with `vault=<configured vault>`, and serialize the return value to JSON wrapped
in a `TextContent` block.

The `mcp` Python SDK is imported LAZILY inside `build_server()` so the rest of
openacad works without it installed.
"""

from __future__ import annotations

import inspect
import json
import types as _types
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from openacad.runtime.tool_registry import get_registry

if TYPE_CHECKING:
    from openacad.vault import Vault


# ──────────────────────────────────────────────────────────────────────────────
# JSON schema derivation from Python type hints
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_hints(fn: Callable[..., Any]) -> dict[str, Any]:
    """Resolve forward-ref annotations on a tool function.

    All tool files use `from __future__ import annotations`, so annotations are
    strings at runtime. We import the real vault types and resolve via
    `get_type_hints`.
    """
    # Import here (not at module top) so importing this module doesn't pull in
    # the entire vault subsystem.
    from openacad.vault import AtomicNote, Chunk, Relation, Source, Span, Vault

    localns = {
        "Vault": Vault,
        "AtomicNote": AtomicNote,
        "Chunk": Chunk,
        "Source": Source,
        "Span": Span,
        "Relation": Relation,
    }
    return get_type_hints(fn, include_extras=True, localns=localns)


def _is_none_type(tp: Any) -> bool:
    return tp is type(None)


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    """If `tp` is `X | None` (or `Optional[X]`), return (X, True). Else (tp, False).

    Handles both `typing.Union[X, None]` and the PEP 604 `X | None` form
    (whose origin is `types.UnionType`, not `typing.Union`).
    """
    origin = get_origin(tp)
    if origin is Union or origin is _types.UnionType:
        args = [a for a in get_args(tp) if not _is_none_type(a)]
        if len(args) == 1 and len(get_args(tp)) == 2:
            return args[0], True
    return tp, False


def _python_type_to_schema(tp: Any) -> dict[str, Any]:
    """Translate a non-Annotated Python type to a minimal JSON schema fragment."""
    # Unwrap Optional first
    tp, _ = _unwrap_optional(tp)

    if tp is str:
        return {"type": "string"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is type(None):
        return {"type": "null"}
    if tp is Any:
        return {}

    origin = get_origin(tp)
    if origin in (list, tuple, set, frozenset):
        args = get_args(tp)
        item_schema = _python_type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        return {"type": "object"}
    if tp is list:
        return {"type": "array"}
    if tp is dict:
        return {"type": "object"}

    # Fallback: accept anything
    return {}


def _param_schema(annotation: Any) -> tuple[dict[str, Any], str | None]:
    """Convert a parameter annotation (possibly `Annotated[T, "desc"]`) to (schema, description)."""
    description: str | None = None
    tp = annotation

    if get_origin(tp) is Annotated:
        args = get_args(tp)
        tp = args[0]
        # Pick the first string-ish piece of metadata as the description
        for meta in args[1:]:
            if isinstance(meta, str):
                description = meta
                break

    schema = _python_type_to_schema(tp)
    if description and "description" not in schema:
        schema = {**schema, "description": description}
    return schema, description


def derive_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Build a JSON schema for the LLM-facing parameters of `fn`.

    Skips the keyword-only `vault: Vault` argument — that's injected by the server.
    """
    sig = inspect.signature(fn)
    hints = _resolve_hints(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for pname, param in sig.parameters.items():
        if pname == "vault":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        annotation = hints.get(pname, param.annotation)
        schema, _desc = _param_schema(annotation)

        # An optional type (`X | None`) OR a default makes the param non-required.
        _, is_optional = _unwrap_optional(
            get_args(annotation)[0] if get_origin(annotation) is Annotated else annotation
        )
        has_default = param.default is not inspect.Parameter.empty

        properties[pname] = schema
        if not (is_optional or has_default):
            required.append(pname)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


# ──────────────────────────────────────────────────────────────────────────────
# Result serialization
# ──────────────────────────────────────────────────────────────────────────────


def _to_json_value(value: Any) -> Any:
    """Recursively convert a tool return value into a JSON-serializable structure."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Pydantic v2 models
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            return dump(mode="json")
        except TypeError:
            return dump()
    if isinstance(value, dict):
        return {str(k): _to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_json_value(v) for v in value]
    # Last resort
    return str(value)


def serialize_result(value: Any) -> str:
    """Serialize a tool's return value to a JSON string for an MCP TextContent block."""
    payload = _to_json_value(value)
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


# ──────────────────────────────────────────────────────────────────────────────
# Tool listing builder (independent of the mcp SDK, used by tests)
# ──────────────────────────────────────────────────────────────────────────────


def build_tool_descriptors() -> list[dict[str, Any]]:
    """Build a list of MCP-ready tool descriptors from the global registry.

    Returns plain dicts — each has `name`, `description`, `inputSchema`. The dict
    form is portable and testable without the `mcp` SDK installed.
    """
    registry = get_registry()
    out: list[dict[str, Any]] = []
    for name in registry.names():
        fn = registry.resolve(name)
        out.append(
            {
                "name": name,
                "description": (fn.__doc__ or "").strip(),
                "inputSchema": derive_input_schema(fn),
            }
        )
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Server construction
# ──────────────────────────────────────────────────────────────────────────────


_FRIENDLY_INSTALL_ERROR = (
    "openacad.mcp requires the optional `mcp` SDK.\n"
    "Install it with:\n"
    "    pip install 'openacad[claude]'\n"
    "or directly:\n"
    "    pip install 'mcp>=1.0'"
)


def _require_mcp() -> Any:
    """Import the mcp SDK lazily; raise a friendly error if missing."""
    try:
        import mcp  # noqa: F401
        import mcp.server  # noqa: F401
        import mcp.server.stdio  # noqa: F401
        import mcp.types  # noqa: F401
        return mcp
    except ImportError as e:
        raise ImportError(_FRIENDLY_INSTALL_ERROR) from e


def build_server(vault: "Vault", *, name: str = "openacad") -> Any:
    """Construct an MCP `Server` bound to the given vault, with every registered tool wired.

    Returns the configured `mcp.server.Server` instance. Caller is responsible for
    running it (see `run_stdio`).
    """
    _require_mcp()
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    server: Any = Server(name)
    registry = get_registry()
    descriptors = build_tool_descriptors()

    mcp_tools = [
        Tool(
            name=d["name"],
            description=d["description"] or None,
            inputSchema=d["inputSchema"],
        )
        for d in descriptors
    ]

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return mcp_tools

    @server.call_tool()
    async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if not registry.has(tool_name):
            return [TextContent(type="text", text=f"Error: unknown tool {tool_name!r}")]
        fn = registry.resolve(tool_name)
        kwargs = dict(arguments or {})
        # Defensive: never let the client smuggle a `vault` override.
        kwargs.pop("vault", None)
        try:
            result = fn(vault=vault, **kwargs)
        except TypeError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except Exception as e:  # noqa: BLE001 — surface error to the MCP client
            return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]
        return [TextContent(type="text", text=serialize_result(result))]

    # Expose for introspection / tests.
    server._openacad_vault = vault  # type: ignore[attr-defined]
    server._openacad_tools = mcp_tools  # type: ignore[attr-defined]
    return server


async def run_stdio(server: Any) -> None:
    """Run the given MCP server over stdio. Blocks until the client disconnects."""
    _require_mcp()
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
