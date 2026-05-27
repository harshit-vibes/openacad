---
type: finding
created_at: '2026-05-24T11:08:34+00:00'
updated_at: '2026-05-24T11:08:34+00:00'
status: active
tags:
- finding
- nlp
- attention
- memory
domain.primary: machine-learning
domain.sub: nlp
evidence.confidence: high
evidence.sample-size: 64
evidence.type: empirical
temporal.year: 2019
---

Empirical profiling of BERT-base at sequence length 1024 shows the attention activations occupy ~58% of total GPU memory, confirming the asymptotic O(n²) characterization in practice.
