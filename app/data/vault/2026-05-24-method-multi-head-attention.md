---
type: method
created_at: '2026-05-24T11:08:34+00:00'
updated_at: '2026-05-24T11:08:34+00:00'
status: active
tags:
- method
- nlp
- attention
- multi-head
domain.primary: machine-learning
domain.sub: nlp
method.class: attention
temporal.year: 2017
relations:
- type: extends
  target: "[[2026-05-24-method-scaled-dot-product-attention]]"
---

Multi-head attention runs h scaled dot-product attention operations in parallel over learned linear projections of Q, K, V. The h outputs are concatenated and projected back to d_model, letting the model attend to information from different representation subspaces.

See also: [[2026-05-24-method-scaled-dot-product-attention]]
