---
type: method
created_at: '2026-05-24T11:08:34+00:00'
updated_at: '2026-05-24T11:08:34+00:00'
status: active
tags:
- method
- nlp
- attention
domain.primary: machine-learning
domain.sub: nlp
method.class: attention
modality.length-regime: <= 4096 tokens
temporal.year: 2017
relations:
- type: extends
  target: "[[2026-05-24-claim-bahdanau-attention]]"
---

Scaled dot-product attention computes Attention(Q, K, V) = softmax(QKᵀ/√d_k) V, where d_k is the key dimension. The 1/√d_k scaling keeps the softmax gradient well-conditioned at large d_k.

See also: [[2026-05-24-claim-bahdanau-attention]]
