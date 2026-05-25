# ⚛️ openacad

**A scholarly research AI agent harness — atomic notes + HITL + meta-evaluation, demonstrated as a 9-rung capability ladder.**

openacad is a research / demo project that asks: *what does an AI research assistant look like when you treat it as a system you can audit, curate, and improve — not a black box you query?*

The answer it argues for: **atomic notes with attributes and relations, curated by humans, drafted and queried by agents whose prompts evolve from rubric feedback.**

---

## The thesis, in one picture

```
                                                  per-query cost
                                              ┌─────────────────┐
  1. 🥶 Cold Read .................................. $0.0009    │ ← baseline
  2. 🧩 Keyword Snippets ............................ $0.0003   ↓
  3. 🧩 Semantic Snippets ........................... $0.0003   ↓ retrieval saves
  4. ⚛️  Atomic Chunks .............................. $0.0038   ↑ but each atom
  5. ⚛️  + Attributes ............................... $0.0036   │   is a denser,
  6. ⚛️  + Relations ................................ $0.0578   ↑   addressable
  7. ⚛️  + Atom Embeddings .......................... $0.0040   │   citation
  8. ⚛️  + HITL Curation ............................ $0.0083   ↑ scholar in loop
  9. ⚛️  Self-Improving Assistant ................... $0.0577   ★ prompts evolve
                                              └─────────────────┘
                                            gpt-4o-mini on SDG briefing,
                                            8-15 canonical questions / rung
```

Each rung adds **one capability** to the previous one. The demo walks you through all nine, side by side, with the actual numbers from real OpenRouter inference runs.

The win condition is *not* "cheapest per query" — it's **lower cost of trust per unit of knowledge**, which the cost curve alone doesn't capture. Rung 9 is more expensive than rung 2 per query, but every cite is a scholar-verified atom with provenance, and the prompts get sharper over time.

---

## What's in the demo

The Streamlit walkthrough has **18 pages**:

```
OVERVIEW
  🏠 Welcome          ─ the framing
  🎓 Conclusion       ─ thesis card + quantitative goodness analysis

THE 9-RUNG LADDER (per-scenario tabbed view — About · Build · Query · Evolve · Results)
  1. 🥶 Cold Read
  2. 🧩 Keyword Snippets
  3. 🧩 Semantic Snippets
  4. ⚛️  Atomic Chunks
  5. ⚛️  + Attributes
  6. ⚛️  + Relations
  7. ⚛️  + Atom Embeddings
  8. ⚛️  + HITL Curation
  9. ⚛️  Self-Improving Assistant   ← thesis-winning configuration

🧰 WORKFLOWS  (scholar-facing, pinned to rung 9)
  📥 Ingest             ─ paper library + chunk/atom rollup
  📜 Compose Artifact   ─ produce paper/chapter/briefing from the vault
  🔍 Assess Artifact    ─ peer-review external doc against the vault

🛠️  OPERATIONS  (operator-facing, pinned to rung 9)
  🧱 Notes & Registry   ─ atoms + attribute/relation schema
  ✍️  Curate            ─ pending drafts + verdict history
  ⭐ Evals & Prompt Hardening  ─ rubrics + prompt versions + meta-eval proposals
  📡 Observability      ─ tool-call traces + latency + cost + errors
```

Per-scenario **Results tab** breaks down:
- 🎯 hero signature metric for that rung
- 📈 Δ vs the previous rung (tokens / citations / latency / cost with % deltas)
- 💰 economics panel (×-multiplier vs cold-read baseline + cost-per-citation)
- 💬 scenario-specific commentary explaining what the numbers mean
- 🧠 atom information density (chars · attrs · rels per atom, for atom-tier scenarios)
- per-question performance table

---

## Quick start

```bash
git clone https://github.com/harshit-vibes/openacad.git
cd openacad/demo

cp .env.example .env             # add your OPENROUTER_API_KEY for live inference
make install                     # uv sync (falls back to pip install -e .)
make app                         # boots Streamlit on http://localhost:8501
```

The repo includes pre-seeded SQLite stores so **every page renders with real data immediately** — no inference required to explore the demo.

To run live inference yourself:
```bash
make api                         # FastAPI on :8000 with Swagger at /docs
make seed                        # re-seed scenarios + PDFs + atoms + scoring datasets
make eval                        # run_baselines + run_atom + eval_report
```

---

## Architecture

Two-layer design — **domain** (pure logic) and **apps** (three interfaces over the same domain).

```
demo/
├── src/openacad/
│   ├── runtime/         SQLite (WAL) + scenario context + LLM provider routing
│   ├── notes/           Atom schema · registry validation · curation · query
│   ├── agents/          Extractor · Synthesizer · Scorer · Meta-Evaluator (PydanticAI)
│   ├── feedback/        Rubrics · verdicts · prompt versioning · scoring
│   ├── artifacts/       Compose (paper/chapter/briefing) + Assess (coverage/critique)
│   ├── projections/     Read-only DTOs for dashboard pages
│   └── scenarios/       The 9 rung definitions
├── apps/
│   ├── api/             FastAPI backend (47 routes)
│   ├── cli/             Typer CLI mirroring every API surface
│   └── streamlit/       18-page walkthrough
│       ├── walkthrough/   global pages (Welcome, Conclusion)
│       ├── scenarios/     9 ladder pages (delegate to scenario_view.py)
│       ├── workflows/     scholar-facing: Ingest · Compose · Assess
│       ├── operations/    operator-facing: Notes/Registry · Curate · Evals · Observability
│       └── views/         shared pin + widgets
└── data/
    ├── shared.sqlite        cross-scenario corpus (papers + chunks)
    ├── embeddings/          MiniLM-L6-v2 embeddings as numpy .npz
    └── vaults/<scenario>/   per-scenario atom store + prompt versions
```

### Key design decisions

- **SQLite (stdlib, WAL mode)** replaced TinyDB — ACID + indexed queries + FTS5 full-text search
- **No external vector DB** — atom embeddings are in-memory cosine over numpy `.npz` files
- **LLM provider pluggable** via `LLM_PROVIDER`. Default: OpenRouter with `gpt-4o-mini`
- **Per-scenario vault**: each rung has its own `data/vaults/<key>/state.sqlite` so capability flags actually mean something — you can't accidentally read atoms-only data into the chunk-only scenarios
- **Atoms are immutable** once accepted; self-improvement happens through **prompt evolution** (regen → promote cycle), not atom mutation
- **No mocked LLMs in tests** — integration tests hit live OpenRouter; smoke tests verify structure

---

## The four agent roles

| Agent | Role | Tools |
|---|---|---|
| 🪓 **Extractor** | Decompose a chunk into atomic notes (claim, definition, indicator, target, …) | `propose_atom`, `lookup_registry`, `validate_attribute` |
| 💬 **Answerer** (Synthesizer) | Multi-tool answering against the atom vault | `query_atoms`, `traverse`, `semantic_search`, `get_atom_full`, `check_contradiction` |
| 🎯 **Scorer** | Score answers against a rubric (accuracy · citation · clarity · registry alignment) | rubric submission |
| 🧬 **Meta-Evaluator** | Read rubric scores + verdict history → propose hardened prompts | `propose_prompt`, `archive_prompt`, `regen_with_proposed` |

Only the rung-9 scenario (`evolving-notes`) has the Meta-Evaluator active. Rungs 1-3 are non-agentic (context-injection answerers). Rungs 4-7 progressively add Answerer capabilities. Rungs 8-9 add Scholar verdicts + Meta-Evaluator.

---

## Tech stack

- **Python 3.11+**
- **Pydantic 2.x** for everything typed (atoms, scenarios, DTOs)
- **PydanticAI** for tool-calling agents
- **OpenRouter** as default LLM provider — `gpt-4o-mini` for both extraction + synthesis
- **SQLite WAL** for storage (no external DB)
- **sentence-transformers** (MiniLM-L6-v2) for embeddings
- **NetworkX** for relation graph traversal
- **Streamlit 1.57+** with `st.navigation(position="hidden")` for the custom sidebar
- **FastAPI + Typer** for the API + CLI surfaces
- **uv** as the primary package manager

---

## Status

This is a **research demo**, not a production system. The code prioritizes legibility over robustness:

- ✅ Every page renders with seeded data out of the box
- ✅ 38+ structural tests green (page loads, projection contracts, scenario decomposition)
- ✅ Real OpenRouter inference behind every scenario's query history
- ⚠️ No production hardening (auth, rate-limiting, multi-tenancy)
- ⚠️ Read-only ops pages (no mutation buttons on Curate / Evals — visible via per-scenario Evolve tab)

The thesis is the substance; the code is the proof-of-concept.

---

## Background reading

Inside the repo, design notes:
- [`atomic-ideas.md`](./atomic-ideas.md) — atomicity philosophy + atomic-note schema
- [`lifecycle.md`](./lifecycle.md) — scholarly research lifecycle, end-to-end
- [`demo/docs/thesis.md`](./demo/docs/thesis.md) — the three-tier thesis (B0 vs B1 vs A)
- [`demo/docs/note-anatomy.md`](./demo/docs/note-anatomy.md) — atom structure
- [`demo/docs/hybrid-retrieval.md`](./demo/docs/hybrid-retrieval.md) — chunk + atom retrieval interplay
- [`demo/docs/tool-calling-agents.md`](./demo/docs/tool-calling-agents.md) — agent loops
- [`demo/docs/superpowers/specs/`](./demo/docs/superpowers/specs/) — implementation design specs

---

## License

MIT — see `LICENSE`.

---

_Built with [Claude Code](https://claude.com/claude-code). The 9-rung ladder, the agent architecture, and every commit on this branch came out of long brainstorm/spec/implement cycles steered by claude.ai/code._
