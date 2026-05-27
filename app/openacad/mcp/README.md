# openacad MCP server

This package adapts the openacad tool registry (`search_vault`, `semantic_search`,
`get_atom`, `propose_atom`, `traverse_relations`, ...) to the
[Model Context Protocol](https://modelcontextprotocol.io/), so any MCP-aware client
can call vault tools as native function calls.

After installing and configuring, MCP-aware clients see ten tools, prefixed
with `mcp__openacad__`:

- `mcp__openacad__search_vault` — FTS5 full-text search
- `mcp__openacad__semantic_search` — MiniLM cosine semantic search
- `mcp__openacad__get_atom` — fetch an atom by id
- `mcp__openacad__incoming` / `mcp__openacad__outgoing` — relation backlinks / forward links
- `mcp__openacad__traverse_relations` — multi-hop BFS over the atom graph
- `mcp__openacad__read_chunk` — raw chunk text + page + offsets
- `mcp__openacad__source_text` — exact source-span substring an atom was extracted from
- `mcp__openacad__check_contradiction` — does a `contradicts` relation connect two atoms?
- `mcp__openacad__propose_atom` — write a draft atom under `.openacad/drafts/`

## Install

```bash
pip install 'openacad[claude]'
```

The `[claude]` extra pulls in the `mcp` Python SDK. Without it, the rest of
openacad still works — but `python -m openacad.mcp` will print a friendly install
hint and exit.

## Path 1 — Claude Code (most common)

Run once, from any project directory:

```bash
claude mcp add openacad -- python -m openacad.mcp --vault ~/Documents/my-research
```

Then in Claude Code:

```
> use openacad to find atoms about transformer attention complexity
```

Claude Code will issue `mcp__openacad__semantic_search` calls automatically.

## Path 2 — Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "openacad": {
      "command": "python",
      "args": [
        "-m",
        "openacad.mcp",
        "--vault",
        "/Users/you/Documents/my-research"
      ]
    }
  }
}
```

Restart Claude Desktop. The hammer icon will list the openacad tools.

## Path 3 — Cursor / Zed / any other MCP client

Same JSON-RPC stdio shape. Configure per client; the command is always
`python -m openacad.mcp --vault <path>`.

## Path 4 — direct test

```bash
python -m openacad.mcp --vault ./data/vault
```

This blocks on stdin and speaks the JSON-RPC stdio MCP wire protocol. Useful for
debugging with `mcp-inspector` or piping fixtures.

## CLI flags

```
python -m openacad.mcp --help
```

- `--vault <path>` (required) — vault directory; created on first run if missing.
- `--name <str>` — server name announced to the client. Default `openacad`.

## How it works

`openacad/mcp/server.py`:

1. Lazy-imports the `mcp` SDK (so a base openacad install without the `[claude]`
   extra still works).
2. Walks the global `ToolRegistry` (populated by `@tool`-decorated functions in
   `openacad/tools/*`).
3. For each tool, derives a JSON schema from its `Annotated[T, "desc"]` type hints,
   stripping the keyword-only `vault: Vault` parameter — the server injects that
   from the configured vault.
4. Wires `list_tools` + `call_tool` handlers on an `mcp.server.Server`. Tool returns
   are recursively JSON-serialized (Pydantic models use `model_dump(mode="json")`)
   and wrapped in a `TextContent` block.

## Troubleshooting

- **"openacad.mcp requires the optional `mcp` SDK"** — run `pip install 'openacad[claude]'`.
- **"could not open vault at /path"** — make sure the parent directory exists and is writable.
- **Tools don't appear in Claude Code** — check `claude mcp list`; if openacad isn't there,
  re-run `claude mcp add` with an absolute path.
