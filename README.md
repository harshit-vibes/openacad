# ⚛️ openacad

**AI-first scholarly research notes. A markdown vault you read in Obsidian. Agents you read as `.md` files. Atoms with source spans you can verify.**

```bash
cd app
make install
openacad init ~/Documents/my-research          # bootstrap a vault
openacad ingest some-paper.pdf --vault ~/Documents/my-research
openacad ask "What does this paper claim?" --vault ~/Documents/my-research
openacad ui                                    # http://localhost:3000
```

Or add it to Claude Code:

```bash
pip install -e 'app[claude]'
claude mcp add openacad -- python -m openacad.mcp --vault ~/Documents/my-research
```

The current product lives in [`app/`](app/). The 9-rung capability ladder that
motivated this design is preserved (frozen) in [`app/museum/`](app/museum/) and
at git tag [`thesis-v1`](https://github.com/harshit-vibes/openacad/tree/thesis-v1).

---

## Architecture in one paragraph

The vault is a directory of plain markdown files. Each `.md` is an **atom** —
one claim, definition, finding, indicator, target, or method. Frontmatter
carries typed attributes + relations to other atoms (Obsidian-compatible
`[[wiki-links]]`). PDF-sourced atoms include a `source:` block with the
exact char-span in the document — `vault.source_text(atom)` returns the exact
substring the atom claims to summarize. The sidecar `.openacad/` directory
travels with the vault: shipped + customized **agents** (`.md` files in
Claude-Code format), **skills** (reusable workflow bundles), **embeddings**
(MiniLM `.npz`), FTS5 index, registry schema, draft queue, activity log.

Five entry points, one substrate:

| Entry point | Use when |
|---|---|
| **`from openacad import Vault, AgentRunner`** | Scripts, notebooks, Python integrations |
| **`openacad <cmd>` CLI** | Day-to-day vault operations from a shell |
| **`openacad ui` / Next.js** | Browse atoms + agents + observability visually |
| **Claude Code via `mcp add openacad`** | Use the vault from Claude Code as native MCP tools |
| **Obsidian / Logseq / any markdown editor** | Just open the vault directory — it's plain `.md` |

---

## What's in the repo

```
openacad/                          # repo root
├── README.md                      # this file
├── LICENSE                        # MIT
├── atomic-ideas.md                # design notes on atom shape
├── lifecycle.md                   # scholarly research lifecycle end-to-end
└── app/                           # ── THE PRODUCT ──
    ├── pyproject.toml             # package: "openacad"
    ├── Makefile · README.md
    ├── openacad/                  # Python package
    │   ├── vault/                 # ★ Engineering IP — single mutation point,
    │   │                          #   round-trip-pure markdown, wiki-link
    │   │                          #   reconciliation, span fidelity (95% test coverage)
    │   ├── agents/                # shipped agents: extractor, answerer, scorer,
    │   │                          #   meta_evaluator (Claude Code .md format)
    │   ├── skills/                # shipped workflow bundles (5 skills)
    │   ├── tools/                 # 10 registered tool functions
    │   ├── runtime/               # AgentRunner over PydanticAI
    │   ├── cli/                   # Typer subcommands (16+)
    │   ├── server/                # FastAPI for the Next.js UI
    │   └── mcp/                   # MCP stdio adapter (optional [claude] extra)
    ├── ui/                        # Next.js 16 + Tailwind + shadcn (9 pages)
    ├── integrations/
    │   └── claude-code/           # drop-in slash commands
    ├── museum/streamlit/          # frozen 9-rung capability ladder demo
    └── data/vault/                # default demo vault (138 atoms)
```

---

## 🌟 The substance — rung 9 in 30 seconds

| | What it gives you |
|---|---|
| ⚛️ **Atoms over chunks** | Addressable, denser citations with provenance |
| 🏷️ **Typed attributes** | Registry-validated metadata, SQL-style filters |
| 🔗 **Relation graph** | Multi-hop traversal across `supports` / `contradicts` / `extends` |
| 🔍 **Atom-level semantic search** | MiniLM embeddings — finds atoms by meaning, not just keywords |
| ✋ **HITL curation** | Scholar accepts / edits / rejects / splits / merges drafts |
| 🧬 **Self-improving agents** | Meta-evaluator reads rubrics → proposes hardened agent `.md` |
| 🛠️ **Multi-tool answerer** | 10 retrieval primitives chained per question |
| 👥 **4-role agent team** | Extractor · Answerer · Scorer · Meta-Evaluator |
| 🔒 **Immutable + versioned** | Atoms immutable; agents tracked in `versions/<role>/v*.md` |
| 📡 **Full observability** | Activity log + tool-call traces + latency + cost |

See [`app/README.md`](app/README.md) for the full architecture + five usage paths.

---

## Thesis evidence (the museum)

Before the current product, openacad was a 9-rung Streamlit demo that walked
through increasing tiers of agent capability and made a quantitative case for
rung 9. That demo is frozen at git tag [`thesis-v1`](https://github.com/harshit-vibes/openacad/tree/thesis-v1)
and lives at `app/museum/streamlit/`.

```bash
cd app
pip install -e '.[museum]'
make museum                        # http://localhost:8585
```

The per-query cost curve across the 9 rungs (gpt-4o-mini on the SDG briefing,
8-15 canonical questions per rung):

```
  1. 🥶 Cold Read .................................. $0.0009    ← baseline
  2. 🧩 Keyword Snippets ............................ $0.0003       retrieval saves
  3. 🧩 Semantic Snippets ........................... $0.0003
  4. ⚛️  Atomic Chunks .............................. $0.0038       atoms = denser
  5. ⚛️  + Attributes ............................... $0.0036       citations
  6. ⚛️  + Relations ................................ $0.0578
  7. ⚛️  + Atom Embeddings .......................... $0.0040
  8. ⚛️  + HITL Curation ............................ $0.0083       scholar in loop
  9. ⚛️  Self-Improving Assistant ................... $0.0577    ★ prompts evolve
```

Rung 9 is more expensive per query than rung 2 — but every cite is a
scholar-verified atom with provenance, and the agents get sharper over time.
That's the trade the product chooses.

---

## License

MIT — see `LICENSE`.

---

_Built with [Claude Code](https://claude.com/claude-code)._
