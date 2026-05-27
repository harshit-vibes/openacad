---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  evidence.confidence: high
  evidence.type: theoretical
  modality.length-regime: '>512 tokens'
  temporal.year: 2017
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-claim-attention-quadratic
  status: active
  tags:
  - claim
  - nlp
  - attention
  - complexity
  type: claim
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations:
- target: 2026-05-24-method-scaled-dot-product-attention
  type: part-of
- target: 2026-05-24-finding-attention-memory-empirical
  type: supported-by
---

The standard scaled dot-product attention mechanism is O(n²) in sequence length, where n is the number of input tokens. Above ~512 tokens with typical hidden sizes, the attention matrix becomes the dominant memory and compute cost of the model.