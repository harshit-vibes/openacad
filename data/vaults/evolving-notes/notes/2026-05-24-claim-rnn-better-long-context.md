---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  evidence.confidence: low
  evidence.type: anecdotal
  modality.length-regime: '>8192 tokens'
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-claim-rnn-better-long-context
  status: active
  tags:
  - claim
  - nlp
  - rnn
  - long-context
  type: claim
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations:
- target: 2026-05-24-claim-attention-quadratic
  type: contradicts
---

Some practitioners report that RNNs handle very long contexts (>8K tokens) more efficiently than vanilla attention, since RNN memory cost is linear in sequence length. The claim is folk knowledge — the supporting evidence is thin and the comparison usually ignores effective context utilisation.