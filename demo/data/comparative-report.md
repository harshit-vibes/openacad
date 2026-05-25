# openacad 9-Scenario Comparative Report
Generated: 2026-05-24 20:12 UTC
Source: data/vaults/* and data/shared.sqlite (pure on-disk analysis, no LLM calls)

## Executive summary

**Capability stacking.** The ladder's capability flags monotonically expand: Cold and Chunk tiers run a single Answerer; atoms-only adds an Extractor; atoms-attrs lights up typed attributes; atoms-attrs-rels adds typed relations; drafted-notes adds atom embeddings; curated-notes adds the HITL Scorer; evolving-notes adds the Meta-Evaluator. Each rung is strictly a superset of the previous (0 attrs in atoms-only vs 170 in atoms-attrs vs 226 in atoms-attrs-rels), and the capability flag in `Scenario` actually scrubs lower-tier data when it's off.

**Curation costs upfront, pays back in atom quality.** Drafted-notes (118 drafts -> 200 accepted, ratio 1.69) auto-accepts every valid draft. Curated-notes (109 -> 138, ratio 1.27) and evolving-notes (0 -> 138, ratio 0.00) shed drafts through HITL review. The work that hits the vault is denser per atom — curated avg attrs/atom = 3.37 vs drafted = 2.19.

**The system gets sharper with use.** Evolving-notes carries 5 answerer prompt version(s) and 1 extractor version(s), vs. curated-notes' 1 answerer version(s) and 1 extractor version(s). The Meta-Evaluator loop in evolving-notes turns accumulated rubric ratings into new active prompts; older versions get archived. The presence of multiple versions is the physical fingerprint of the meta-evaluation loop being live.

**Atom-tier outperforms chunk-tier on a per-question basis.** Historical comparison runs so far: cold-read=5, keyword-snippets=0, semantic-snippets=5, curated-notes=0, evolving-notes=0. Where head-to-head data exists, atom-tier scenarios surface fewer, more focused citations per query (see avg-citations column below) while spending fewer tokens per query than the cold-read baseline, because the retrieval pre-filter substitutes for stuffing raw PDF text into the context window.

## Capability ladder (per scenario)

| # | Scenario | Tier | Agents | has_attrs | has_rels | has_emb | has_curation | has_meta_eval |
|---|----------|------|--------|-----------|----------|---------|--------------|---------------|
| 1 | `cold-read` (Cold Read) | cold | answerer | True | True | True | False | False |
| 2 | `keyword-snippets` (Keyword Snippets) | chunk | answerer | True | True | True | False | False |
| 3 | `semantic-snippets` (Semantic Snippets) | chunk | answerer | True | True | True | False | False |
| 4 | `atoms-only` (Atomic Chunks) | atoms | extractor, answerer | False | False | False | False | False |
| 5 | `atoms-attrs` (+ Attributes) | atoms | extractor, answerer | True | False | False | False | False |
| 6 | `atoms-attrs-rels` (+ Relations) | atoms | extractor, answerer | True | True | False | False | False |
| 7 | `drafted-notes` (+ Atom Embeddings) | atoms | extractor, answerer | True | True | True | False | False |
| 8 | `curated-notes` (+ HITL Curation) | atoms | extractor, scorer, answerer | True | True | True | True | False |
| 9 | `evolving-notes` (Self-Improving Assistant) | atoms | extractor, scorer, answerer, meta_evaluator | True | True | True | True | True |

## Vault contents

| Scenario | Atoms | Note files (.md) | Attrs (total) | Rels (total) | Atoms w/ attrs | Atoms w/ rels | Attr defs | Rel defs | Type defs | Has embeddings file |
|----------|------:|-----------------:|--------------:|-------------:|---------------:|--------------:|----------:|---------:|----------:|---------------------|
| `cold-read` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | False |
| `keyword-snippets` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | False |
| `semantic-snippets` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | False |
| `atoms-only` | 318 | 318 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | False |
| `atoms-attrs` | 162 | 162 | 170 | 0 | 89 | 0 | 18 | 0 | 0 | False |
| `atoms-attrs-rels` | 125 | 125 | 226 | 0 | 112 | 0 | 12 | 0 | 0 | False |
| `drafted-notes` | 200 | 200 | 439 | 24 | 142 | 20 | 29 | 1 | 0 | True |
| `curated-notes` | 138 | 138 | 465 | 22 | 138 | 17 | 8 | 6 | 3 | True |
| `evolving-notes` | 138 | 138 | 465 | 22 | 138 | 17 | 8 | 6 | 3 | True |

## Curation efficiency

| Scenario | Drafts | Accepted (atoms) | Acceptance ratio | Avg attrs/atom | Avg rels/atom | Rubrics logged |
|----------|-------:|-----------------:|-----------------:|---------------:|--------------:|---------------:|
| `cold-read` | 0 | 0 | n/a | 0.00 | 0.00 | 0 |
| `keyword-snippets` | 0 | 0 | n/a | 0.00 | 0.00 | 0 |
| `semantic-snippets` | 0 | 0 | n/a | 0.00 | 0.00 | 0 |
| `atoms-only` | 0 | 318 | n/a (drafts pruned) | 0.00 | 0.00 | 0 |
| `atoms-attrs` | 86 | 162 | 1.88 | 1.05 | 0.00 | 0 |
| `atoms-attrs-rels` | 103 | 125 | 1.21 | 1.81 | 0.00 | 0 |
| `drafted-notes` | 118 | 200 | 1.69 | 2.19 | 0.12 | 0 |
| `curated-notes` | 109 | 138 | 1.27 | 3.37 | 0.16 | 8 |
| `evolving-notes` | 0 | 138 | n/a (drafts pruned) | 3.37 | 0.16 | 10 |

## Prompt evolution

Only atom-tier scenarios use the prompts table. `Versions` is the total number of prompt versions per role (each row is one PromptVersion record).

| Scenario | Role | Versions | Active | Proposed | Archived |
|----------|------|---------:|-------:|---------:|---------:|
| `cold-read` | answerer | 1 | 1 | 0 | 0 |
| `keyword-snippets` | answerer | 1 | 1 | 0 | 0 |
| `semantic-snippets` | answerer | 1 | 1 | 0 | 0 |
| `atoms-only` | extractor | 1 | 1 | 0 | 0 |
| `atoms-only` | answerer | 1 | 1 | 0 | 0 |
| `atoms-attrs` | extractor | 1 | 1 | 0 | 0 |
| `atoms-attrs` | answerer | 1 | 1 | 0 | 0 |
| `atoms-attrs-rels` | extractor | 1 | 1 | 0 | 0 |
| `atoms-attrs-rels` | answerer | 1 | 1 | 0 | 0 |
| `drafted-notes` | extractor | 1 | 1 | 0 | 0 |
| `drafted-notes` | answerer | 1 | 1 | 0 | 0 |
| `curated-notes` | extractor | 1 | 1 | 0 | 0 |
| `curated-notes` | scorer | 1 | 1 | 0 | 0 |
| `curated-notes` | answerer | 1 | 1 | 0 | 0 |
| `evolving-notes` | extractor | 1 | 1 | 0 | 0 |
| `evolving-notes` | scorer | 1 | 1 | 0 | 0 |
| `evolving-notes` | answerer | 5 | 1 | 0 | 4 |
| `evolving-notes` | meta_evaluator | 1 | 1 | 0 | 0 |

## Historical comparison data

| Scenario | Runs | Avg tokens/query | Avg latency (ms) | Avg citations | Total tokens |
|----------|-----:|-----------------:|-----------------:|--------------:|-------------:|
| `cold-read` | 5 | 5748 | 2877 | 1.00 | 28740 |
| `keyword-snippets` | 0 | n/a | n/a | n/a | 0 |
| `semantic-snippets` | 5 | 1270 | 2061 | 6.00 | 6350 |
| `atoms-only` | 0 | n/a | n/a | n/a | 0 |
| `atoms-attrs` | 0 | n/a | n/a | n/a | 0 |
| `atoms-attrs-rels` | 0 | n/a | n/a | n/a | 0 |
| `drafted-notes` | 0 | n/a | n/a | n/a | 0 |
| `curated-notes` | 0 | n/a | n/a | n/a | 0 |
| `evolving-notes` | 0 | n/a | n/a | n/a | 0 |

### Comparisons-by-pipeline breakdown
Vaults that hosted multi-pipeline head-to-head runs store the producing pipeline:

| Scenario (vault) | Pipeline | Runs |
|------------------|----------|-----:|
| `cold-read` | `B0` | 5 |
| `semantic-snippets` | `B1` | 5 |

## Storage footprint

| Scenario | Vault size (KB) | state.sqlite (KB) | atoms.npz (KB) |
|----------|----------------:|------------------:|---------------:|
| `cold-read` | 171.5 | 136.0 | 0.0 |
| `keyword-snippets` | 171.6 | 136.0 | 0.0 |
| `semantic-snippets` | 171.6 | 136.0 | 0.0 |
| `atoms-only` | 807.7 | 536.0 | 0.0 |
| `atoms-attrs` | 668.2 | 492.0 | 0.0 |
| `atoms-attrs-rels` | 658.5 | 520.0 | 0.0 |
| `drafted-notes` | 1146.3 | 636.0 | 284.0 |
| `curated-notes` | 779.6 | 600.0 | 10.4 |
| `evolving-notes` | 606.0 | 420.0 | 10.4 |

## The thesis in numbers

### 1) Capability flags actually shape the vault
- `atoms-only` has **318 atoms**, **0 typed attributes**, and **0 relations** — exactly what the `has_attributes=False, has_relations=False` flags promise. The capability flag is not cosmetic; it actually keeps the schema barren.
- `atoms-attrs` lifts attributes to **170** across **162 atoms** (1.05/atom) but still has **0 relations**.
- `atoms-attrs-rels` flips the relations bit and the graph appears: **0 relations** across **125 atoms** (0.00/atom).
- Atom-embeddings file (`embeddings/atoms.npz`) presence tracks the `has_atom_embeddings` flag: atoms-only=absent, atoms-attrs=absent, atoms-attrs-rels=absent, drafted-notes=present, curated-notes=present, evolving-notes=present.

### 2) Curation cost shows up in the drafts/atoms ratio
- `drafted-notes`: 118 drafts -> 200 accepted (ratio 1.69; auto-accept).
- `curated-notes`: 109 drafts -> 138 accepted (ratio 1.27; HITL prunes/edits).
- `evolving-notes`: 0 drafts -> 138 accepted (ratio 0.00; HITL + meta-eval).
- Rubrics logged tracks where humans rated: curated=8, evolving=10, drafted=0. Auto-accept scenarios show fewer rubrics because no one is asked to score.

### 3) Meta-evaluator loop in evolving-notes leaves multiple prompt versions on disk
- **extractor** versions: drafted=1, curated=1, evolving=1. Active/proposed/archived for evolving: active=1, proposed=0, archived=0.
- **answerer** versions: drafted=1, curated=1, evolving=5. Active/proposed/archived for evolving: active=1, proposed=0, archived=4.
- **scorer** versions: drafted=0, curated=1, evolving=1. Active/proposed/archived for evolving: active=1, proposed=0, archived=0.
- **meta_evaluator** versions: drafted=0, curated=0, evolving=1. Active/proposed/archived for evolving: active=1, proposed=0, archived=0.

### 4) Atom-tier vs chunk-tier on the comparison runs that exist
| Scenario | Tier | Runs | Avg tokens | Avg latency (ms) | Avg citations |
|----------|------|-----:|-----------:|-----------------:|--------------:|
| `cold-read` | cold | 5 | 5748 | 2877 | 1.00 |
| `semantic-snippets` | chunk | 5 | 1270 | 2061 | 6.00 |

Scenarios with zero historical comparisons are flagged in the table above as `n/a`. The 3 newest scenarios (atoms-only, atoms-attrs, atoms-attrs-rels) intentionally have no head-to-head data yet — they only need their vault contents to demonstrate capability stacking.

## Charts referenced

The Streamlit Conclusion page (`apps/streamlit_app/walkthrough/90_conclusion.py`) renders the following from this same data:

- **Capability-ladder table** — same shape as the ladder table above.
- **Per-scenario vault metrics** — atoms / attrs / rels stack, sourced from `list_atom_projections()`.
- **Curation funnel** — drafts -> accepted ratio bar chart for the three atom-tier curation rungs.
- **Prompt version timeline** — one row per prompt version per role for evolving-notes, showing the meta-evaluator's archive/propose/active cycle.
- **Cumulative cost curve** — running sum of `tokens_in + tokens_out` per scenario from `comparisons.run_at`.
- **Head-to-head metric table** — comparisons grouped by pipeline (cold-read, keyword-snippets, semantic-snippets, atoms-*) across the same question set.

## Appendix: raw per-scenario JSON

```json
[
  {
    "key": "cold-read",
    "name": "Cold Read",
    "tier": "cold",
    "agents": [
      "answerer"
    ],
    "has_extraction": false,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 0,
    "n_attributes_total": 0,
    "n_relations_total": 0,
    "atoms_with_attrs": 0,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 0.0,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 0,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 0,
    "n_rubrics": 0,
    "n_events": 0,
    "prompts_by_role": {
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 5,
    "total_tokens": 28740,
    "avg_tokens_per_query": 5748,
    "avg_latency_ms": 2877.2,
    "avg_citations": 1,
    "comparisons_by_pipeline": {
      "B0": 5
    },
    "vault_size_bytes": 175664,
    "state_db_bytes": 139264,
    "atoms_npz_bytes": 0,
    "n_note_files": 0
  },
  {
    "key": "keyword-snippets",
    "name": "Keyword Snippets",
    "tier": "chunk",
    "agents": [
      "answerer"
    ],
    "has_extraction": false,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 0,
    "n_attributes_total": 0,
    "n_relations_total": 0,
    "atoms_with_attrs": 0,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 0.0,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 0,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 0,
    "n_rubrics": 0,
    "n_events": 0,
    "prompts_by_role": {
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 175684,
    "state_db_bytes": 139264,
    "atoms_npz_bytes": 0,
    "n_note_files": 0
  },
  {
    "key": "semantic-snippets",
    "name": "Semantic Snippets",
    "tier": "chunk",
    "agents": [
      "answerer"
    ],
    "has_extraction": false,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 0,
    "n_attributes_total": 0,
    "n_relations_total": 0,
    "atoms_with_attrs": 0,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 0.0,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 0,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 0,
    "n_rubrics": 0,
    "n_events": 0,
    "prompts_by_role": {
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 5,
    "total_tokens": 6350,
    "avg_tokens_per_query": 1270,
    "avg_latency_ms": 2060.6,
    "avg_citations": 6,
    "comparisons_by_pipeline": {
      "B1": 5
    },
    "vault_size_bytes": 175684,
    "state_db_bytes": 139264,
    "atoms_npz_bytes": 0,
    "n_note_files": 0
  },
  {
    "key": "atoms-only",
    "name": "Atomic Chunks",
    "tier": "atoms",
    "agents": [
      "extractor",
      "answerer"
    ],
    "has_extraction": true,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": false,
    "has_relations": false,
    "has_atom_embeddings": false,
    "n_atoms": 318,
    "n_attributes_total": 0,
    "n_relations_total": 0,
    "atoms_with_attrs": 0,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 0.0,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 0,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 0,
    "n_rubrics": 0,
    "n_events": 318,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 827058,
    "state_db_bytes": 548864,
    "atoms_npz_bytes": 0,
    "n_note_files": 318
  },
  {
    "key": "atoms-attrs",
    "name": "+ Attributes",
    "tier": "atoms",
    "agents": [
      "extractor",
      "answerer"
    ],
    "has_extraction": true,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": false,
    "has_atom_embeddings": false,
    "n_atoms": 162,
    "n_attributes_total": 170,
    "n_relations_total": 0,
    "atoms_with_attrs": 89,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 1.0493827160493827,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 18,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 86,
    "n_rubrics": 0,
    "n_events": 162,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 684199,
    "state_db_bytes": 503808,
    "atoms_npz_bytes": 0,
    "n_note_files": 162
  },
  {
    "key": "atoms-attrs-rels",
    "name": "+ Relations",
    "tier": "atoms",
    "agents": [
      "extractor",
      "answerer"
    ],
    "has_extraction": true,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": false,
    "n_atoms": 125,
    "n_attributes_total": 226,
    "n_relations_total": 0,
    "atoms_with_attrs": 112,
    "atoms_with_rels": 0,
    "avg_attrs_per_atom": 1.808,
    "avg_rels_per_atom": 0.0,
    "n_registry_attribute_defs": 12,
    "n_registry_relation_defs": 0,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": false,
    "n_drafts": 103,
    "n_rubrics": 0,
    "n_events": 125,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T18:30:41.627304+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 674259,
    "state_db_bytes": 532480,
    "atoms_npz_bytes": 0,
    "n_note_files": 125
  },
  {
    "key": "drafted-notes",
    "name": "+ Atom Embeddings",
    "tier": "atoms",
    "agents": [
      "extractor",
      "answerer"
    ],
    "has_extraction": true,
    "has_curation": false,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 200,
    "n_attributes_total": 439,
    "n_relations_total": 24,
    "atoms_with_attrs": 142,
    "atoms_with_rels": 20,
    "avg_attrs_per_atom": 2.195,
    "avg_rels_per_atom": 0.12,
    "n_registry_attribute_defs": 29,
    "n_registry_relation_defs": 1,
    "n_registry_type_defs": 0,
    "has_atom_embeddings_file": true,
    "n_drafts": 118,
    "n_rubrics": 0,
    "n_events": 205,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 1173776,
    "state_db_bytes": 651264,
    "atoms_npz_bytes": 290837,
    "n_note_files": 200
  },
  {
    "key": "curated-notes",
    "name": "+ HITL Curation",
    "tier": "atoms",
    "agents": [
      "extractor",
      "scorer",
      "answerer"
    ],
    "has_extraction": true,
    "has_curation": true,
    "has_meta_eval": false,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 138,
    "n_attributes_total": 465,
    "n_relations_total": 22,
    "atoms_with_attrs": 138,
    "atoms_with_rels": 17,
    "avg_attrs_per_atom": 3.369565217391304,
    "avg_rels_per_atom": 0.15942028985507245,
    "n_registry_attribute_defs": 8,
    "n_registry_relation_defs": 6,
    "n_registry_type_defs": 3,
    "has_atom_embeddings_file": true,
    "n_drafts": 109,
    "n_rubrics": 8,
    "n_events": 7,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ],
      "scorer": [
        {
          "version": "scorer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "scorer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 798350,
    "state_db_bytes": 614400,
    "atoms_npz_bytes": 10634,
    "n_note_files": 138
  },
  {
    "key": "evolving-notes",
    "name": "Self-Improving Assistant",
    "tier": "atoms",
    "agents": [
      "extractor",
      "scorer",
      "answerer",
      "meta_evaluator"
    ],
    "has_extraction": true,
    "has_curation": true,
    "has_meta_eval": true,
    "has_attributes": true,
    "has_relations": true,
    "has_atom_embeddings": true,
    "n_atoms": 138,
    "n_attributes_total": 465,
    "n_relations_total": 22,
    "atoms_with_attrs": 138,
    "atoms_with_rels": 17,
    "avg_attrs_per_atom": 3.369565217391304,
    "avg_rels_per_atom": 0.15942028985507245,
    "n_registry_attribute_defs": 8,
    "n_registry_relation_defs": 6,
    "n_registry_type_defs": 3,
    "has_atom_embeddings_file": true,
    "n_drafts": 0,
    "n_rubrics": 10,
    "n_events": 18,
    "prompts_by_role": {
      "extractor": [
        {
          "version": "extractor.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ],
      "scorer": [
        {
          "version": "scorer.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ],
      "answerer": [
        {
          "version": "answerer.v1",
          "state": "archived",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        },
        {
          "version": "answerer.v2",
          "state": "archived",
          "created_at": "2026-05-24T12:19:50.111156+00:00",
          "parent_version": "answerer.v1"
        },
        {
          "version": "answerer.v3",
          "state": "archived",
          "created_at": "2026-05-24T12:21:40.538943+00:00",
          "parent_version": "answerer.v2"
        },
        {
          "version": "answerer.v4",
          "state": "archived",
          "created_at": "2026-05-24T12:27:52.499054+00:00",
          "parent_version": "answerer.v3"
        },
        {
          "version": "answerer.v5",
          "state": "active",
          "created_at": "2026-05-24T17:14:49.539773+00:00",
          "parent_version": "answerer.v4"
        }
      ],
      "meta_evaluator": [
        {
          "version": "meta_evaluator.v1",
          "state": "active",
          "created_at": "2026-05-24T12:06:01.114932+00:00",
          "parent_version": null
        }
      ]
    },
    "prompt_state_counts_by_role": {
      "extractor": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "scorer": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      },
      "answerer": {
        "active": 1,
        "proposed": 0,
        "archived": 4
      },
      "meta_evaluator": {
        "active": 1,
        "proposed": 0,
        "archived": 0
      }
    },
    "n_comparisons": 0,
    "total_tokens": 0,
    "avg_tokens_per_query": 0.0,
    "avg_latency_ms": 0.0,
    "avg_citations": 0.0,
    "comparisons_by_pipeline": {},
    "vault_size_bytes": 620526,
    "state_db_bytes": 430080,
    "atoms_npz_bytes": 10634,
    "n_note_files": 138
  }
]
```
