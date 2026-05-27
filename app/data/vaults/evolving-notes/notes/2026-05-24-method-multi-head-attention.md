---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  method.class: attention
  temporal.year: 2017
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-method-multi-head-attention
  status: active
  tags:
  - method
  - nlp
  - attention
  - multi-head
  type: method
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations:
- target: 2026-05-24-method-scaled-dot-product-attention
  type: extends
---

Multi-head attention runs h scaled dot-product attention operations in parallel over learned linear projections of Q, K, V. The h outputs are concatenated and projected back to d_model, letting the model attend to information from different representation subspaces.