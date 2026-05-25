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

## 🌟 Salient features of rung 9 — the Self-Improving Assistant

The thesis-winning configuration. Every capability below is **off** by default; you have to opt in one rung at a time, which is why the demo IS the ladder. Rung 9 has all of them turned on.

### ⚛️ Atoms, not chunks
The vault stores **atomic notes** — claim, definition, indicator, finding, target, method — each with its own id, body, source, attributes, and relations. Atoms are addressable across queries; chunks aren't. An answer cites `atom-58ab0c43` (a specific claim) instead of "chunk 12 of paper 3" (an anonymous text window).

### 🏷️ Typed attributes (registry-validated)
Every atom carries structured metadata: `{sdg_target: "5.2", year: 2030, evidence_strength: "strong", indicator_type: "outcome"}`. The **registry** is a per-vault schema layer that promotes recurring attribute keys into typed definitions with `allowed_values`, usage counts, and orphan detection. The agent can SQL-style filter the vault — `query_atoms(type="claim", where={sdg_target: "5.2"})` — instead of grepping prose.

### 🔗 Relation graph for multi-hop reasoning
Atoms link to other atoms via typed edges: `supports`, `contradicts`, `extends`, `refutes`, `part_of`, `cites`. The Answerer can call `traverse(atom_id, via=["contradicts"], hops=2)` to chain evidence across the vault. Some questions that are impossible at chunk tier become natural here ("show me claims about SDG 5 that contradict claims about SDG 8").

### 🔍 Atom-level semantic search
MiniLM-L6-v2 embeddings persist as numpy `.npz` files — not chunks, **atoms**. The Answerer's `semantic_search(query)` finds fuzzy-similar atoms by meaning, complementing the SQL-style attribute filter. No external vector DB; cosine search runs in-memory.

### ✋ HITL curation (scholar gates the vault)
Every atom proposed by the Extractor lands in a **drafts queue**. A scholar accepts / edits / rejects / deprecates. Only accepted atoms enter the vault. The vault has ~30% fewer atoms than the raw extraction, but every remaining atom carries a scholar's fingerprint, not just the LLM's. Curated atoms are **immutable** — there's no "edit accepted atom" path; revisions create new atoms with provenance back to the original.

### 🧬 Self-improving prompts (Meta-Evaluator loop)
The **Meta-Evaluator** reads rubric scores and verdict history, identifies patterns ("Extractor is producing too-broad claims when atomicity drops below 0.7"), and **proposes** a hardened prompt revision. Proposals don't auto-apply — a scholar promotes them. The active prompt for each agent role evolves: v1 → v2 → v3 over time, each version traceable to the rubric/verdict evidence that motivated it. This is the **only** rung where today's system is structurally different from yesterday's system, and the difference is scholar-promoted, not auto-applied.

### 🛠️ Multi-tool answerer (5 retrieval primitives)
The Answerer is a tool-calling agent (PydanticAI) with:

| Tool | Purpose |
|---|---|
| `query_atoms` | SQL-style attribute filter — typed `where` clauses |
| `semantic_search` | Cosine search over atom embeddings |
| `traverse` | Graph traversal via relation type, bounded by hops |
| `get_atom_full` | Fetch full body when a summary is insufficient |
| `check_contradiction` | Symmetric edge-presence check between two atoms |

The agent picks tools per question — typically chains 8-30 calls (plan → retrieve → refine → cite) for a single query. Every call is logged with latency, args, results, and any error.

### 👥 Four-role agent team

| Role | What it does | Active rungs |
|---|---|---|
| 🪓 **Extractor** | Decomposes chunks into atoms with attributes + suggested relations | 4-9 |
| 💬 **Answerer** | Tool-calling synthesis over the vault | 4-9 |
| 🎯 **Scorer** | Rates answers against a rubric (accuracy / citation / clarity / registry alignment) | 8-9 |
| 🧬 **Meta-Evaluator** | Reads scorer + scholar feedback, proposes prompt hardening | 9 only |

Each agent has its own scenario-aware prompt version. The Meta-Evaluator can target the Extractor's prompt, the Answerer's prompt, even its own.

### 🔒 Auditable, versioned, immutable where it matters
- **Atoms** — immutable once accepted. New evidence creates new atoms, not edits.
- **Prompts** — versioned with `parent_version`, `state` (proposed/active/archived), `based_on_events` (the rubric/verdict ids that triggered the proposal), `accept_rate`.
- **Tool calls** — every call logged with `session_id`, args, latency, n_results, error_message. The Observability page reads this directly; no separate telemetry layer.
- **Verdicts** — every scholar accept/edit/reject is an `EvalEvent` row, timestamped, with the draft id and any edit delta.

### 📡 Full observability (no logfire dependency needed)
The Observability page surfaces:
- KPI row: total tool calls · avg latency · total cost · errors
- Latency histogram (8 buckets, 0-100ms → 10s+)
- Cost rollup by role (Extractor / Answerer / Scorer / Meta-Evaluator) and by day
- Tool-call table (filterable by agent, tool, session)
- Activity feed (chronological merge of tool calls + verdicts + prompt promotions + meta-eval proposals)
- Error log (any tool call where `error_message is not null`)

All from the same SQLite tables the agents write to — no separate observability backend.

### 🎯 Where the cost actually goes
The 64× cost spike vs cold-read isn't waste. It's:

1. **Multi-tool agent loops** — 8-30 tool calls per question with intermediate reasoning
2. **Relation traversal** — unbounded graph walks (production would cap at hops=2)
3. **Evolved synthesis prompt discipline** — the rung-9 Answerer prompt is markedly more thorough than v1, producing longer, better-grounded answers
4. **Half the answers cite nothing rather than weakly grounding** — when no atom is a strong-enough citation, the evolved prompt outputs an uncited answer rather than a fabricated cite. You're paying for the agent's *restraint*

What you DON'T pay for: re-extraction (atoms are persistent), re-curation (verdicts persist), re-embedding (atoms only embed once at acceptance).

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
