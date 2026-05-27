"""build_server constructs a Server populated with every registered tool."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="optional `mcp` SDK not installed")


def test_build_server_registers_every_tool(tmp_vault):
    """The MCP server exposes exactly the tools in the global registry."""
    from openacad.mcp.server import build_server
    from openacad.runtime.tool_registry import get_registry

    server = build_server(tmp_vault)
    registry = get_registry()

    mcp_tools = getattr(server, "_openacad_tools")
    mcp_names = sorted(t.name for t in mcp_tools)
    registry_names = sorted(registry.names())

    assert mcp_names == registry_names
    assert len(mcp_tools) == len(registry_names)
    # Sanity: at least the canonical ten ship-tools are present.
    assert len(mcp_tools) >= 10


def test_build_server_binds_vault(tmp_vault):
    from openacad.mcp.server import build_server

    server = build_server(tmp_vault)
    assert getattr(server, "_openacad_vault") is tmp_vault


def test_build_server_name(tmp_vault):
    from openacad.mcp.server import build_server

    server = build_server(tmp_vault, name="acme")
    # mcp.server.Server stores the name as `.name`
    assert getattr(server, "name", None) == "acme"


def test_descriptors_match_registry():
    """The dict-only descriptor builder can run without the mcp SDK touching it."""
    from openacad.mcp.server import build_tool_descriptors
    from openacad.runtime.tool_registry import get_registry

    descriptors = build_tool_descriptors()
    registry = get_registry()

    assert sorted(d["name"] for d in descriptors) == sorted(registry.names())
    for d in descriptors:
        assert isinstance(d["description"], str)
        assert isinstance(d["inputSchema"], dict)
        assert d["inputSchema"]["type"] == "object"


def test_serialize_result_handles_atom_list(tmp_vault):
    """serialize_result must JSON-encode a list of AtomicNote pydantic models.

    The call_tool path runs every tool return value through serialize_result,
    so the round-trip must work even when the list is empty.
    """
    import json as _json

    from openacad.mcp.server import serialize_result

    # Empty vault → empty result list.
    empty = serialize_result(tmp_vault.search("anything"))
    assert _json.loads(empty) == []

    # A None-returning tool (e.g. get_atom for a missing id) serializes to JSON null.
    none_out = serialize_result(None)
    assert _json.loads(none_out) is None

    # A dict (propose_atom's return shape) round-trips.
    dict_out = serialize_result({"path": "/x", "draft_id": "draft-001"})
    parsed = _json.loads(dict_out)
    assert parsed == {"path": "/x", "draft_id": "draft-001"}

    # A bool round-trips (check_contradiction).
    assert _json.loads(serialize_result(False)) is False


def test_call_tool_round_trip(tmp_vault):
    """End-to-end: invoke the registered call_tool handler against an empty vault."""
    import asyncio
    import json as _json

    from openacad.mcp.server import build_server
    from mcp import types as mcp_types

    server = build_server(tmp_vault)
    # The decorator registers a handler keyed by CallToolRequest.
    handler = server.request_handlers[mcp_types.CallToolRequest]

    req = mcp_types.CallToolRequest(
        method="tools/call",
        params=mcp_types.CallToolRequestParams(
            name="search_vault",
            arguments={"query": "anything"},
        ),
    )
    server_result = asyncio.run(handler(req))
    # ServerResult wraps a CallToolResult; the content is a list of TextContent.
    call_result = server_result.root
    assert not getattr(call_result, "isError", False)
    contents = call_result.content
    assert len(contents) == 1
    assert contents[0].type == "text"
    assert _json.loads(contents[0].text) == []
