# Museum — the frozen 9-rung thesis demo

This directory preserves the original openacad demonstration: a 9-rung capability
ladder that walks through increasing tiers of AI agent capability — from a
naive cold-read PDF dump up to a self-improving meta-evaluator loop — and
makes the case for why rung 9 (Self-Improving Assistant) is the right
configuration for an AI-first scholarly research platform.

It's the thesis evidence behind the current openacad product (`openacad/` Python
package, `ui/` Next.js app). After v0.1.0 it is **frozen** and no longer
maintained — git tag `thesis-v1` marks the last actively-developed state.

## Run it

```bash
pip install -e '.[museum]'     # installs streamlit + pandas
make museum                    # boots Streamlit on :8585
# OR
openacad museum                # same thing via the new CLI
```

Then open http://localhost:8585.

## What's in here

```
museum/streamlit/
├── streamlit_app.py        # entrypoint + sidebar (Welcome · 9 ladder · Conclusion)
├── scenario_view.py        # per-scenario 5-tab template (About · Build · Query · Evolve · Results)
├── widgets.py              # shared scenario picker + agent-map components
├── walkthrough/
│   ├── 00_welcome.py       # the thesis pitch
│   └── 90_conclusion.py    # head-to-head runner · cost curve · capability matrix
│                           #   + Goodness tab (quantitative goodness analysis)
└── scenarios/              # 9 three-line delegators (one per rung)
    ├── cold_read.py · keyword_snippets.py · semantic_snippets.py
    ├── atoms_only.py · atoms_attrs.py · atoms_attrs_rels.py
    ├── drafted_notes.py · curated_notes.py · evolving_notes.py
```

The cross-cutting Workflows (Ingest · Compose · Assess) and Operations
(Notes & Registry · Curate · Evals · Observability) pages that the museum
once hosted have been **replaced by the new Next.js UI** (`ui/`) which is the
canonical product surface going forward.

## Why keep it?

- **Comparative evidence.** The cost curve, capability matrix, and goodness
  analysis on the Conclusion page are the quantitative argument for the
  rung-9 design that the new product implements.
- **Provenance.** Anyone evaluating the new product can see exactly which
  earlier configurations were considered and rejected, and on what numbers.
- **No surprise dependencies.** The museum is OPT-IN via the `[museum]` extra,
  so the core product `pip install openacad` doesn't pull Streamlit or pandas.

## Caveats

- The museum is read against the SQLite seed in `data/vaults/<scenario>/` and
  `data/shared.sqlite`, not the new markdown vault at `data/vault/`. The two
  data stores coexist; neither overwrites the other.
- The legacy CLI under `python -m openacad.cli._legacy_main` is what the
  Streamlit pages call into for live actions. The new CLI (`openacad <cmd>`)
  does not drive the museum.
- LLM-dependent demos (the "Run head-to-head" button on Conclusion, the
  per-scenario Query tab) require an `OPENROUTER_API_KEY` in `.env`. The
  static panels (cost curve, capability matrix, goodness) work offline from
  the seeded comparison data.
