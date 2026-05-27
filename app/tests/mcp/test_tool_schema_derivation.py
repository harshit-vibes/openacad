"""For each registered tool, the derived MCP inputSchema matches the type hints
and never exposes the keyword-only `vault` argument."""

from __future__ import annotations

from openacad.mcp.server import build_tool_descriptors, derive_input_schema
from openacad.runtime.tool_registry import get_registry


def test_no_descriptor_exposes_vault():
    """The `vault: Vault` parameter is server-injected; clients must never see it."""
    for d in build_tool_descriptors():
        props = d["inputSchema"].get("properties", {})
        assert "vault" not in props, f"tool {d['name']!r} leaks `vault` into its schema"
        assert "vault" not in d["inputSchema"].get("required", [])


def test_every_registered_tool_has_a_schema():
    descriptors_by_name = {d["name"]: d for d in build_tool_descriptors()}
    for name in get_registry().names():
        assert name in descriptors_by_name, f"missing descriptor for {name!r}"
        schema = descriptors_by_name[name]["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema


def test_search_vault_schema_shape():
    """search_vault has `query: str` (required) and `top_k: int = 10` (optional)."""
    from openacad.tools.search_vault import search_vault

    schema = derive_input_schema(search_vault)
    assert schema["type"] == "object"
    props = schema["properties"]
    assert props["query"]["type"] == "string"
    assert "Keyword or phrase" in props["query"]["description"]
    assert props["top_k"]["type"] == "integer"
    assert "vault" not in props
    assert schema.get("required") == ["query"]


def test_get_atom_schema_required_atom_id():
    """get_atom takes only `atom_id: str` (required) plus the hidden vault."""
    from openacad.tools.get_atom import get_atom

    schema = derive_input_schema(get_atom)
    props = schema["properties"]
    assert list(props.keys()) == ["atom_id"]
    assert props["atom_id"]["type"] == "string"
    assert schema["required"] == ["atom_id"]


def test_outgoing_schema_optional_type():
    """outgoing has a `type: str | None = None` arg that must NOT be required."""
    from openacad.tools.outgoing import outgoing

    schema = derive_input_schema(outgoing)
    props = schema["properties"]
    assert "atom_id" in props
    assert "type" in props
    assert schema.get("required") == ["atom_id"]


def test_traverse_relations_schema():
    """traverse_relations: atom_id required, max_hops + type optional."""
    from openacad.tools.traverse_relations import traverse_relations

    schema = derive_input_schema(traverse_relations)
    props = schema["properties"]
    assert props["atom_id"]["type"] == "string"
    assert props["max_hops"]["type"] == "integer"
    assert "type" in props
    assert schema.get("required") == ["atom_id"]


def test_propose_atom_schema_lists_and_optionals():
    """propose_atom exercises list[str], list[dict] | None, int | None, str | None."""
    from openacad.tools.propose_atom import propose_atom

    schema = derive_input_schema(propose_atom)
    props = schema["properties"]
    # `body` is the only required parameter (everything else has a default).
    assert schema.get("required") == ["body"]
    assert props["body"]["type"] == "string"
    assert props["type"]["type"] == "string"
    # tags: list[str] | None
    assert props["tags"]["type"] == "array"
    assert props["tags"]["items"]["type"] == "string"
    # relations: list[dict] | None
    assert props["relations"]["type"] == "array"
    assert props["relations"]["items"]["type"] == "object"
    # page: int | None
    assert props["page"]["type"] == "integer"
    # doc_id: str | None
    assert props["doc_id"]["type"] == "string"


def test_check_contradiction_schema_two_strings():
    from openacad.tools.check_contradiction import check_contradiction

    schema = derive_input_schema(check_contradiction)
    props = schema["properties"]
    assert props["atom_a"]["type"] == "string"
    assert props["atom_b"]["type"] == "string"
    assert sorted(schema["required"]) == ["atom_a", "atom_b"]


def test_descriptions_carried_through():
    """Annotated[T, "desc"] metadata should end up as the schema's description field."""
    from openacad.tools.semantic_search import semantic_search

    schema = derive_input_schema(semantic_search)
    assert "description" in schema["properties"]["query"]
    assert schema["properties"]["query"]["description"]
