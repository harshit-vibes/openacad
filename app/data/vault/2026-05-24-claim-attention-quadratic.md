---
type: claim
created_at: '2026-05-24T11:08:34+00:00'
updated_at: '2026-05-24T11:08:34+00:00'
status: active
tags:
- claim
- nlp
- attention
- complexity
domain.primary: machine-learning
domain.sub: nlp
evidence.confidence: high
evidence.type: theoretical
modality.length-regime: ">512 tokens"
temporal.year: 2017
relations:
- type: part-of
  target: "[[2026-05-24-method-scaled-dot-product-attention]]"
- type: supported-by
  target: "[[2026-05-24-finding-attention-memory-empirical]]"
---

The standard scaled dot-product attention mechanism is O(n²) in sequence length, where n is the number of input tokens. Above ~512 tokens with typical hidden sizes, the attention matrix becomes the dominant memory and compute cost of the model.

See also: [[2026-05-24-method-scaled-dot-product-attention]] [[2026-05-24-finding-attention-memory-empirical]]
