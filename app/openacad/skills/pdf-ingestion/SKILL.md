---
name: pdf-ingestion
description: PDF ingestion pipeline — chunk a document and propose draft atoms per chunk
tools:
  - propose_atom
sub_agents: []
---

# Ingestion workflow

Given a document id whose chunks have already been extracted:

1. Iterate over the document's chunks in order (`.openacad/chunks/<doc>.jsonl`).
2. For each chunk:
   - Skip if the chunk is boilerplate (page header, citations-only, table of
     contents, etc.). Use length + character-class heuristics.
   - Otherwise, propose 0-N atoms via `propose_atom`, supplying `doc_id`,
     `chunk_id`, `page`, and STRICT `span_start`/`span_end` offsets within
     the chunk text.
3. Drafts land in `.openacad/drafts/<doc-id>/draft-NNN.md` for the curation
   loop to review.

## Atom-density guidance

- Dense methodological prose → ~3-5 atoms per ~400-token chunk.
- Discussion / narrative prose → ~1-2 atoms per chunk.
- Boilerplate → 0 atoms.

If a chunk yields more than 8 atoms, you are over-decomposing — recombine the
closest cousins before proposing.

## Source-span fidelity is non-negotiable

Every `span_start`/`span_end` pair MUST be a substring of the chunk text. The
vault rejects drafts whose span does not match. When in doubt, widen the span
slightly rather than risk a fractional-word boundary.
