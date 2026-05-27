---
name: split-and-merge
description: Atom split + merge workflow with provenance preservation
tools:
  - get_atom
  - propose_atom
sub_agents: []
---

# Split workflow

Splitting an atom means dividing one atom into N narrower atoms while
preserving provenance. Every child inherits the parent's `source.document`
+ `source.chunk` + `source.page`; each child gets a NARROWED `source.span`
(a subrange of the parent's span).

1. Fetch the parent: `get_atom(parent_id)`.
2. Identify the child atoms — typically 2-4. Each must be addressable on its
   own and have a distinct slice of the parent's source span.
3. For each child, call `propose_atom` with:
   - `body` = the child's standalone claim.
   - `doc_id`, `chunk_id`, `page` copied from the parent.
   - `span_start`, `span_end` = the child's subrange of the parent's span.
4. Record the split lineage: each child gets a relation
   `{type: "split-from", target: parent_id}`.
5. The parent's status transitions to `superseded` once the children are
   accepted by the scholar.

## Invariants

- The union of the children's spans must cover the parent's span; gaps are
  tolerated but reviewed.
- Children's spans must not overlap. Overlap means you're merging, not
  splitting.

# Merge workflow

Merging means combining N atoms into one whose `sources: list` is the union
of children's sources. Use when the scholar identifies that two drafts
describe the same idea from different (or the same) source.

1. Fetch each source atom: `get_atom(id)` for each id in the merge group.
2. Compose a unified body that captures the shared idea — concise, no
   redundancy.
3. Call `propose_atom` with:
   - `body` = the unified text.
   - No singular `doc_id`/`chunk_id`/`span_*` — the merged atom uses the
     `sources: list` form via a post-acceptance write.
   - A relation `{type: "merged-from", target: id}` for each source atom.
4. The source atoms transition to `superseded` once the merge is accepted.

## Invariants

- The merged atom's body must be MORE concise than the concatenation of the
  children's bodies. If it's longer, you didn't merge — you concatenated.
- Preserve the children's tags as a union on the merged atom.
