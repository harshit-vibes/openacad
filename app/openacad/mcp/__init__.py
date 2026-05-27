"""openacad.mcp — Model Context Protocol adapter.

Exposes the openacad tool registry as an MCP stdio server so MCP-aware clients
(Claude Code, Claude Desktop, Cursor, Zed, ...) can call vault tools natively.

Run as a module:

    python -m openacad.mcp --vault ~/Documents/my-research

Add to Claude Code:

    claude mcp add openacad -- python -m openacad.mcp --vault ~/Documents/my-research

The `mcp` Python SDK is an OPTIONAL dependency. Install with::

    pip install 'openacad[claude]'

This package imports the SDK lazily — the rest of openacad works without it.
"""

from __future__ import annotations

__all__ = ["build_server", "run_stdio"]


def __getattr__(name: str):
    if name in ("build_server", "run_stdio"):
        from openacad.mcp.server import build_server, run_stdio
        return {"build_server": build_server, "run_stdio": run_stdio}[name]
    raise AttributeError(f"module 'openacad.mcp' has no attribute {name!r}")
