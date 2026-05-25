---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  method.class: attention
  modality.length-regime: <= 4096 tokens
  temporal.year: 2017
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-method-scaled-dot-product-attention
  status: active
  tags:
  - method
  - nlp
  - attention
  type: method
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations:
- target: 2026-05-24-claim-bahdanau-attention
  type: extends
---

Scaled dot-product attention computes Attention(Q, K, V) = softmax(QKᵀ/√d_k) V, where d_k is the key dimension. The 1/√d_k scaling keeps the softmax gradient well-conditioned at large d_k.