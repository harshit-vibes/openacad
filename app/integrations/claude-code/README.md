# Claude Code integrations for openacad

Three slash commands that wrap the openacad CLI so you can use it from inside any
Claude Code session.

## Install

```bash
cp /Users/hkc/Documents/openacad/app/integrations/claude-code/commands/*.md ~/.claude/commands/
```

(adjust the source path if you cloned openacad somewhere else).

Slash commands in `~/.claude/commands/` are auto-discovered by Claude Code.

## Available commands

| Command | What it does |
| --- | --- |
| `/openacad-ask <question>` | Ask a question against your openacad vault and summarize the cited atoms. |
| `/openacad-curate` | Open the human-in-the-loop draft curation loop. |
| `/openacad-evolve` | Run the meta-evaluator and report which prompts were promoted. |

Each command shells out to the `openacad` CLI binary; if that isn't on PATH it
falls back to running the module from the local `.venv`.

## See also: the MCP server

The slash commands above call the CLI. For *native* tool calls inside Claude Code
(`mcp__openacad__search_vault`, `mcp__openacad__semantic_search`, ...), set up
the MCP server instead:

```bash
claude mcp add openacad -- python -m openacad.mcp --vault ~/Documents/my-research
```

See `openacad/mcp/README.md` for the full integration guide (Claude Desktop,
Cursor, Zed).
