---
name: atom-curation
description: HITL workflow for accepting, editing, rejecting, splitting, and merging draft atoms
tools:
  - propose_atom
  - search_vault
  - get_atom
sub_agents:
  - scorer
---

# The curation loop

For each pending draft in `.openacad/drafts/<doc-id>/`:

1. Read the draft and its source span (use the `source-verification` skill).
2. Compute a score by delegating to the `scorer` sub-agent.
3. Present to the scholar with: body, source quote, score, neighbouring atoms.
4. Apply the scholar's verdict:
   - `accept` → move draft to vault root, set `status: active`
   - `edit` → open editor, then accept
   - `reject` → archive in `.openacad/drafts/<doc-id>/.rejected/`
   - `split` → invoke the `split-and-merge` skill (split branch)
   - `merge` → mark this draft as part of a merge batch
5. Log every action to `.openacad/activity.jsonl`.

## Ordering heuristics

- Score-descending so the easiest wins go first.
- Cluster by source chunk so the scholar's context stays warm.
- Surface candidate-merge groups (high pairwise semantic similarity) together.
