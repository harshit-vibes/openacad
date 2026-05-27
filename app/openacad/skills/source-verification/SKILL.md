---
name: source-verification
description: Verifies that an atom's source span is a strict substring of the chunk it claims
tools:
  - source_text
  - read_chunk
sub_agents: []
---

# Verification workflow

Before quoting or citing an atom, verify that its source span actually supports
the claim.

1. Resolve the chunk: `read_chunk(atom.source.chunk)`.
2. Resolve the substring: `source_text(atom.id)`. This returns
   `chunk.text[span.start:span.end]` — the exact substring, no normalisation.
3. Confirm the substring:
   - Is non-empty.
   - Contains the keywords / proper nouns that appear in the atom body.
   - Is not just whitespace / a section header.
4. If any check fails, mark the atom as `span-misaligned` and surface for human
   review.

## Why this matters

The atom's promise to the scholar is: "every claim I make is grounded in a
substring you can find on disk." Verification protects that promise. An atom
whose span doesn't support its body is worse than no atom — it gives the
scholar false confidence.

## Heuristics

- Spans under 30 chars are suspicious; they often catch fragments.
- Spans over 600 chars defeat the purpose of atomicity; suggest a narrower
  span and possibly an atom split.
- Spans that begin mid-word or mid-sentence are off-by-one bugs from the
  extractor; widen to the nearest word boundary.
