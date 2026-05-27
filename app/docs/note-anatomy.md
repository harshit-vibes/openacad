# Note Anatomy — the canonical schema

This document is the authoritative spec for what an atomic note is in this project. Code, prompts, and UI must conform to it.

## Five sections

Every atomic note is a markdown file with two parts:

1. **YAML frontmatter** containing four grouped sections:
   - `metas` — identity and housekeeping
   - `origin` — where this atom came from (provenance)
   - `attributes` — scholar-curated key-value facts
   - `relations` — typed edges to other atoms
2. **Markdown body** — the `content` section. The human-readable atom in the scholar's own voice. One idea, one note.

That's five sections total. They map 1:1 to Pydantic models in `api/models/atom.py`.

## Full schema (example atom)

```markdown
---
metas:
  id: 2026-05-24-claim-attention-quadratic     # stable kebab-case, project-unique
  type: claim                                  # claim | method | finding (v1)
  status: active                               # draft | active | archived
  created_at: 2026-05-24T10:00:00Z             # ISO-8601 UTC
  updated_at: 2026-05-24T10:00:00Z             # bumped on edit
  tags: [claim, nlp, attention]                # flat list for fast filtering

origin:
  source_id: paper-vaswani-2017                # PaperSource.id; null for seeded
  chunk_ids: [c-0042, c-0043]                  # Chunk.ids this atom was drawn from
  page_range: [3, 4]
  prompt_version: extraction.v1                # null for seeded
  scholar_action: accepted                     # accepted | edited | seeded

attributes:                                    # flat scalar k-v; dotted-namespace convention
  domain.primary: machine-learning
  domain.sub: nlp
  evidence.type: theoretical
  evidence.confidence: high

relations:                                     # typed edges, {type, target}
  - type: extends
    target: 2026-05-24-claim-bahdanau-attention
  - type: part-of
    target: 2026-05-24-method-scaled-dot-product-attention
---

The standard attention mechanism is O(n²) in sequence length, which becomes the
dominant cost above ~512 tokens for typical hidden sizes.
```

## Section reference

### `metas` — identity and housekeeping

| Field | Type | Notes |
|------|------|-------|
| `id` | string | Stable, kebab-case, prefix `YYYY-MM-DD-{type}-{slug}`. Never reused. |
| `type` | enum | `claim` \| `method` \| `finding` (v1). New types proposed via registry, never auto-created. |
| `status` | enum | `active` (default) \| `draft` (uncommitted) \| `archived`. |
| `created_at` | ISO-8601 | UTC, set once at first commit. |
| `updated_at` | ISO-8601 | UTC, bumped on every edit. |
| `tags` | string[] | Flat list. Convention: `[type, primary-domain, …]`. Filterable; not registered. |

### `origin` — provenance (the audit trail)

Bound to the philosophical commitment in `~/Documents/openacad/atomic-ideas.md` §11.3: an atom out of context is meaningless. Every atom carries enough to reconstruct *why we believe it and where it came from*.

| Field | Type | Notes |
|------|------|-------|
| `source_id` | string \| null | The `PaperSource.id` this atom came from. Null for seeded/hand-authored. |
| `chunk_ids` | string[] | Chunks the atom rests on. Anchors to specific text spans. |
| `page_range` | [int, int] \| null | Page span in the source PDF. |
| `prompt_version` | string \| null | The extraction-prompt version that drafted this. Null for seeded. Used by the eval loop. |
| `scholar_action` | enum | `accepted` (LLM draft kept as-is) \| `edited` (LLM draft modified) \| `seeded` (hand-authored). |

### `attributes` — scholar-curated facts (open vocabulary, registry-governed)

Flat key-value pairs. Keys are kebab-case strings; the dotted-namespace convention (`evidence.confidence`, `domain.primary`) lets the registry group them at view time. Values are scalars: `string`, `number`, `bool`, or `null`.

**Why scalar-only at v1**: keeps the registry's `value_type` cleanly enumerable, keeps SQLite projections trivially queryable, keeps PydanticAI's structured outputs reliable. The schema can widen to lists/objects later without breaking existing atoms.

**Explicit `null` is meaningful** — it signals "we asked but the source did not say." Distinguishes missing-by-omission from missing-by-absence.

**Registry growth** — a key that appears in ≥3 distinct accepted atoms auto-registers as `vault/registry/attributes/attr-{key}.md`. New keys can appear freely on draft atoms; promotion happens silently at the threshold.

### `relations` — typed edges (registry-validated)

A list of objects. Required keys: `type`, `target`.

- `type`: kebab-case relation name. ≥3 distinct uses → auto-registers as `rel-{type}.md`.
- `target`: the `id` of another atomic note in this vault.

Per-relation attributes (e.g. confidence, page-range) are a v2 addition. The schema upgrade is purely additive — add an optional `meta: dict` field; old atoms parse unchanged.

### `content` — the body

Plain markdown. One idea. Should stand alone for a reader who arrived via search. Links are for follow-on, not prerequisites.

## Atomicity contract

Disciplines the system enforces, not metaphysical claims:

1. **One idea per note.** If you find yourself writing "and also," split.
2. **The body stands alone.** A reader landing on this note via search should understand the idea without opening anything else.
3. **Origin is structural.** An AI-extracted atom without `origin.source_id` and `origin.chunk_ids` is a bug, not a permitted state.
4. **Atomicity is a parameter, not a property** (per `atomic-ideas.md` §9). Recursive containment is supported via relations; nothing prevents bundling at retrieval-time.

## Strict registry enforcement at write time

Every commit goes through `registry_service.validate(atom)`. The write is rejected if:

- an attribute key's `value_type` doesn't match the supplied value
- an attribute's `allowed_values` (enum) doesn't include the supplied value
- an attribute is used on an atom whose `metas.type` is not in `applicable_types`
- a relation's source atom type is not in `source_types`
- a relation's target atom type is not in `target_types`
- a relation's `target` atom id does not exist

Unknown keys (not yet registered) **pass through** — they're eligible for auto-promotion at the ≥3-uses threshold.

## Why this schema works for AI-assisted workflows

- The frontmatter is **machine-grade**: every section is typed and trivially queryable. Asking "which atoms have an `evidence.sample-size` attribute?" is an O(1) SQLite lookup.
- The relations are **graph-grade**: NetworkX rebuilds the typed edge structure at boot. Cypher-style traversals (`extends → contradicts → supported-by`) become Python dict walks.
- The body is **embedding-grade**: short, focused text vectorizes cleanly. The cosine neighborhood of one atom is meaningful in a way that the neighborhood of a 4000-character chunk is not.
- The origin is **audit-grade**: every claim in a synthesis traces to the chunk it came from and the prompt version that drafted it.

The combination is what makes `POST /compare` win: structured filter + graph traversal + semantic + body retrieval beats vector-alone on tokens, and the per-atom citation beats page-range citation on legibility.

## Upgrade contract (nothing is foreclosed)

All v2 additions are pure additive fields with defaults. Old atoms parse unchanged:

- widen `AttrValue` from scalars to `scalar | list | dict` for richer values (`evidence.sample-size: {value, unit, uncertainty}`)
- add `Relation.namespace` (inferential / evidential / citational / compositional / causal / methodological)
- add `Relation.meta: dict` for per-edge attributes
- add `Origin.additional_sources: list[Origin]` for multi-paper atoms
- add `Origin.derived_from: list[atom_id]` for synthesized atoms
- add `Origin.edit_distance`, `Origin.actor` for richer eval signal
