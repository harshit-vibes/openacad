# openacad

**AI-first scholarly research platform. Markdown vault of atomic notes + a Claude-Code-style agent harness.**

This directory is the product. It contains:

- `openacad/` — the Python library + CLI + internal FastAPI server + MCP adapter
- `ui/` — the Next.js 16 playground UI
- `museum/` — the frozen 9-rung capability-ladder demo that motivated this design (see [museum/README.md](museum/README.md))
- `data/vault/` — a default markdown vault, pre-seeded with 138 atoms from the SDG briefing demo

## Install

```bash
cd app
make install                              # uv sync (or pip install -e .)
pip install -e '.[claude]'                # optional: MCP support for Claude Code
pip install -e '.[museum]'                # optional: Streamlit thesis tour
```

Set up the LLM provider:

```bash
cp .env.example .env
# then edit .env to set OPENROUTER_API_KEY=<your-key>
```

## Five ways to use it

### 1. Python library (the most direct path)

```python
from openacad import Vault, AgentRunner

vault = Vault("~/Documents/my-research")     # opens / creates the vault + .openacad/
runner = AgentRunner(vault)

result = runner.run("answerer", question="What does SDG 1 say about poverty thresholds?")
print(result.answer)
print(result.citations)   # e.g. ['atom-58ab0c43', 'atom-fa72']

# direct vault access
for atom in vault.search("poverty 2030", top_k=5):
    print(atom.path, atom.attributes)
```

### 2. CLI (Obsidian-CLI inspired)

```bash
openacad init ~/Documents/my-research          # bootstrap a vault
openacad ingest some-paper.pdf                 # copy + extract metadata
openacad chunk <doc-id>                        # PDF → chunks (with char offsets)
openacad extract <doc-id>                      # chunks → drafts via Extractor agent
openacad curate                                # accept / edit / reject / split / merge
openacad ask "What does SDG 1 say?"            # answerer + citations
openacad evolve                                # meta-evaluator → prompt proposals
openacad query incoming atom-fa72              # graph traversal
openacad query source atom-fa72                # exact source-chunk substring
openacad agents diff answerer                  # see proposed prompt edits
openacad agents promote answerer               # archive current → activate proposed
```

Every command has `--help`. The `query` subcommand documents the `rg` / `yq`
equivalent for each pattern — the vault is plain markdown so any shell tool
works against it.

### 3. Next.js UI (the playground)

```bash
# terminal 1
PYTHONPATH=. .venv/bin/python -m uvicorn openacad.server.main:app --port 8000
# terminal 2
cd ui && pnpm install && pnpm dev
# open http://localhost:3000
```

9 pages: Welcome · Vault (atom browser) · Agents · Ingest · Compose · Assess · Curate · Observability · Museum.

### 4. From Claude Code (via MCP)

```bash
pip install -e '.[claude]'                                                                           # installs the MCP SDK
claude mcp add openacad -- python -m openacad.mcp --vault ~/Documents/my-research
```

That's it. Restart Claude Code and 10 tools become available:
`mcp__openacad__search_vault`, `mcp__openacad__semantic_search`,
`mcp__openacad__traverse_relations`, `mcp__openacad__get_atom`,
`mcp__openacad__propose_atom`, `mcp__openacad__check_contradiction`,
`mcp__openacad__incoming`, `mcp__openacad__outgoing`,
`mcp__openacad__read_chunk`, `mcp__openacad__source_text`.

Plus drop-in slash commands at [`integrations/claude-code/commands/`](integrations/claude-code/commands/) —
`/openacad-ask`, `/openacad-curate`, `/openacad-evolve`.

### 5. From Obsidian / Logseq / any markdown editor

The vault is just `.md` files. Open the vault directory in Obsidian and it
works — frontmatter is parsed, `[[wiki-links]]` resolve, attributes show in
the side panel.

## Architecture (one diagram)

```
~/Documents/my-research/                ← your vault — opens in Obsidian
├── atom-fa72.md                        ← one atom per file (frontmatter + body)
├── atom-3c41.md
├── ...
└── .openacad/                          ← sidecar — travels with the vault
    ├── config.yaml
    ├── agents/                         ← Claude-Code-format .md agents
    │   ├── extractor.md  answerer.md  scorer.md  meta_evaluator.md
    │   ├── versions/<role>/v1.md v2.md v3.md     ← promoted history
    │   └── proposed/                              ← meta-evaluator's pending edits
    ├── skills/                                    ← reusable workflow bundles
    │   ├── atom-curation/SKILL.md
    │   ├── pdf-ingestion/SKILL.md
    │   ├── source-verification/SKILL.md
    │   ├── split-and-merge/SKILL.md
    │   └── relation-traversal/SKILL.md
    ├── documents/<doc-id>.pdf + .meta.yaml        ← ingested originals
    ├── chunks/<doc-id>.jsonl                      ← extracted text + char offsets
    ├── drafts/<doc-id>/draft-NNN.md               ← pending extractor proposals
    ├── index/
    │   ├── embeddings.npz                         ← MiniLM atom embeddings
    │   ├── registry.yaml                          ← attribute + relation schema
    │   └── cache.sqlite                           ← FTS5 mirror + tool-call log
    └── activity.jsonl                             ← append-only event log
```

Each atom carries provenance back to the exact char-span in the source chunk:

```markdown
---
type: claim
status: active
domain: poverty
sdg_target: "1.2"
source:
  document: doi-10-xxxx-abc
  chunk: chunk-fa72
  span: { start: 1234, end: 1456 }
  page: 5
relations:
  - type: supports
    target: "[[atom-9bc1]]"
---

The SDG 1 target seeks to halve the share of people living in extreme
poverty (under $2.15/day) by 2030 per [[atom-9bc1]].
```

`vault.source_text(atom)` returns the exact substring `chunk.text[1234:1456]`
of the source PDF — the "trust test" that lets a scholar verify any atom
against its origin.

## Agents are markdown files

Every agent is a `.md` file in Claude-Code format. Edit them with any text editor:

```markdown
---
name: extractor
description: Decomposes document chunks into atomic notes
model: openai/gpt-4o-mini
tools:
  - search_vault
  - get_atom
  - propose_atom
skills:
  - source-verification
  - relation-traversal
---

You are an extraction agent. Given a document chunk with text and char offsets,
you propose 0-N atomic notes...
```

These files are loaded by openacad's `AgentRunner` (over PydanticAI) AND directly
by Claude Code if you copy them to `.claude/agents/`. Same files, two runtimes.

## Test coverage

```bash
make test                                    # full suite
PYTHONPATH=. .venv/bin/python -m pytest tests/vault/ --cov=openacad/vault
```

- `openacad/vault/` — **95% coverage** (157 tests). The engineering IP.
- Total: **300+ tests** across vault, runtime, agents, skills, tools, CLI, MCP server.

## Background — the museum

The current product is rung 9 of a 9-rung capability ladder that was used to
explore the design space. The earlier rungs (Cold Read → Atomic Chunks → +
Attributes → ...) are preserved in [museum/streamlit/](museum/) — a frozen
Streamlit tour you can boot with `make museum`.

See [museum/README.md](museum/README.md) for the why.

## License

MIT — see `LICENSE` at the repo root.
