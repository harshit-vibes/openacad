# Registry as the Schema Layer

## Why the registry is a core entity, not a glossary

If the registry just lists "keys we've seen," it's a glossary — useful but not load-bearing.

If the registry holds **definitions** with enough teeth — what values are valid, what relation targets are allowed, what semantic role each key plays — then it becomes the **schema layer** that converts a vault of free-form notes into a queryable knowledge graph.

This is the Apache AGE insight applied to a personal research vault: one underlying store, three query languages (SQL over relational, Cypher over graph, cosine over embeddings), unified by a schema. For this demo:

- **SQLite** holds the structured projection of every atom (flat-indexed attributes). It serves the **SQL-style** queries: *"all claims where `evidence.type=empirical` and `domain.sub=nlp`."*
- **NetworkX** holds the typed relations graph (atoms = nodes, relations = typed edges). It serves the **graph-style** queries: *"all atoms reachable from atom-X via `contradicts → supported-by`."*
- **In-memory MiniLM embeddings** serve the **semantic** queries: *"atoms similar in meaning to this question."*
- **The registry** is the schema shared by all three. It says what attributes exist, what values they take, what relations exist, what their valid sources/targets are. Without it, all three become brittle.

The demo's flagship query becomes: *"find claims in NLP that contradict findings supported by empirical evidence."* That's **SQLite filter → NetworkX hop → SQLite filter → NetworkX hop → SQLite filter**, composed in one call. Raw RAG cannot do this. The registry is what makes it tractable.

## Three registries

All under `vault/registry/`, one-file-per-entry, written as markdown with YAML frontmatter.

### Attribute entries — `vault/registry/attributes/attr-{key}.md`

```yaml
---
key: evidence.confidence
namespace: evidence
description: "How strongly the source supports this atom"
value_type: enum                       # string | number | bool | enum | date
allowed_values: [high, medium, low]    # only present when value_type=enum
applicable_types: [claim, finding]     # which atom types may use this key
usage_count: 17
first_seen: 2026-05-24T10:00:00Z
auto_registered: true
---

Scholar-editable notes on when to use this key vs others.
```

### Relation entries — `vault/registry/relations/rel-{key}.md`

```yaml
---
key: extends
namespace: inferential
description: "Source atom generalizes or builds on the target atom"
inverse: extended-by                   # optional; powers reverse traversal
source_types: [claim, finding]
target_types: [claim]
usage_count: 23
first_seen: 2026-05-24T10:00:00Z
auto_registered: true
---

Scholar-editable guidance.
```

### Type entries — `vault/registry/types/type-{name}.md`

```yaml
---
key: claim
description: "An assertion the source paper argues to be true"
suggested_attributes: [domain.primary, evidence.type, evidence.confidence]
suggested_relations: [extends, contradicts, supported-by]
example_atom: 2026-05-24-claim-attention-quadratic
first_seen: 2026-05-24T10:00:00Z
auto_registered: false                 # types always scholar-approved
---
```

## The three "types" — disambiguated

Because "type" is overloaded, here's the clean mapping:

| Where it lives | Field | What it holds | Example |
|----------------|-------|---------------|---------|
| on an atom (in `metas`) | `type` | the *kind of atomic note* | `claim` / `method` / `finding` |
| on an attribute registry entry | `value_type` | the *data type* the value must be | `string` / `number` / `bool` / `enum` / `date` |
| on an attribute or relation registry entry | `applicable_types` (attrs) / `source_types` + `target_types` (rels) | which *atom types* are allowed to use this attribute or be a relation source/target | `[claim, finding]` |

## What each field powers at runtime

**`atom.metas.type`** drives:
- which extraction prompt section is selected
- filter facets on the `/notes` browse view
- registry's `applicable_types` checks at write time

**registry `value_type`** drives:
- write-time validation ("`evidence.sample-size` received `high` but `value_type` is `number` → reject")
- which UI input renders for the curate-edit form (number stepper, date picker, enum dropdown)
- which SQLite query operators are offered (`==` always; `>` / `<` / `between` only for `number`)
- LLM extraction prompt guidance ("this attribute should be an integer")

**registry `applicable_types` / `source_types` / `target_types`** drives:
- write-time validation ("`extends` relation target has type `method`, but registry says target_types must be `[claim]` → reject")
- LLM extraction prompt narrowing ("when extracting a `method` atom, do not suggest the `evidence.confidence` attribute")
- registry browser groupings ("which attributes apply to claims?")

## Strict enforcement

Every commit goes through `registry_service.validate(atom)`. **Writes are rejected** if any of:

- attribute key's `value_type` doesn't match the supplied value
- attribute's `allowed_values` (enum) doesn't include the supplied value
- attribute used on an atom whose `metas.type` is not in `applicable_types`
- relation's source atom type is not in `source_types`
- relation's target atom type is not in `target_types`
- relation's `target` atom id does not exist

The scholar must either fix the atom or first widen the registry entry before commit.

**Unknown keys** (not yet registered) **pass through** — they are eligible for auto-promotion at the ≥3-uses threshold (below).

## Auto-promotion thresholds

| Registry | Auto-promote? | Threshold | Trigger |
|----------|---------------|-----------|---------|
| Attributes | yes (silent) | ≥3 distinct accepted atoms use the key | on every `curate.accept` event |
| Relations | yes (silent) | ≥3 distinct accepted atoms use the relation `type` | on every `curate.accept` event |
| Types | **no — always proposed** | n/a | new type appearing in a draft enters `proposals` queue in SQLite |

When an attribute auto-registers, the `value_type` is inferred:
- all observed values cast to the same Python type → use that
- otherwise → default to `string`
- if the same set of ≤6 distinct values appears → propose `enum` with those `allowed_values`

The scholar can always edit the registry entry after auto-registration.

## Schema-evolution audit trail

Every registry change appends to `vault/registry/schema-evolution.md`. Append-only.

```markdown
## 2026-05-24T14:02:17Z — auto-register
- kind: attribute
- key: sample-size
- trigger: 3rd distinct use (in atoms a-001, a-007, a-014)
- file: vault/registry/attributes/attr-sample-size.md

## 2026-05-24T14:05:33Z — proposal
- kind: type
- key: hypothesis
- trigger: first appearance in draft dr-0032
- state: pending review

## 2026-05-24T14:08:12Z — promote (type)
- kind: type
- key: hypothesis
- approved_by: scholar
- file: vault/registry/types/type-hypothesis.md
```

The file is the ground-truth log for "how did the schema get here?" Never edited, never rewritten.

## In-memory `Schema` cache

`api/services/schema.py::Schema` loads all registry entries at boot into a single in-memory object. Consulted by:

- **extraction** — for prompt context injection (relevant attribute/relation definitions for the source paper's domain)
- **curate** — for write-time validation
- **retrieval** — for query planning (cardinality estimates from `usage_count`)
- **registry promotion** — for threshold checks and inference

`Schema.reload()` is called after every registry change. Hot reload, no service restart needed.

## Why these rules, not others

- **Threshold of 3** for auto-promotion: two is coincidence; five is too high to capture regularities in a small vault. Three is the sweet spot.
- **Silent auto-promote for attributes and relations**: the cost of a wrong promotion is low (entries can be edited or deprecated), and prompting the scholar for every promotion creates friction that suppresses curation.
- **Always-explicit for types**: a wrong type promotion is structurally disruptive (it changes what the system extracts). Worth the prompt.
- **Strict write-time enforcement**: matches the "deterministic scholar control" principle from the thesis. The scholar gets fast, precise errors and either fixes the atom or widens the registry; both paths leave the system in a coherent state.
- **Append-only audit trail**: matches the provenance principle (`atomic-ideas.md` §11.3). The schema's history is part of the schema.
