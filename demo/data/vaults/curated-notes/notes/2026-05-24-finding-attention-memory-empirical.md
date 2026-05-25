---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  evidence.confidence: high
  evidence.sample-size: 64
  evidence.type: empirical
  temporal.year: 2019
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-finding-attention-memory-empirical
  status: active
  tags:
  - finding
  - nlp
  - attention
  - memory
  type: finding
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations: []
---

Empirical profiling of BERT-base at sequence length 1024 shows the attention activations occupy ~58% of total GPU memory, confirming the asymptotic O(n²) characterization in practice.