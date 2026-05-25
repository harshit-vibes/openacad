---
attributes:
  domain.primary: machine-learning
  domain.sub: nlp
  evidence.confidence: high
  evidence.sample-size: 4500000
  evidence.type: empirical
  temporal.year: 2017
metas:
  created_at: '2026-05-24T11:08:34Z'
  id: 2026-05-24-finding-bleu-transformer-wmt2014
  status: active
  tags:
  - finding
  - nlp
  - machine-translation
  - benchmarks
  type: finding
  updated_at: '2026-05-24T11:08:34Z'
origin:
  chunk_ids: []
  page_range: null
  prompt_version: null
  scholar_action: seeded
  source_id: null
relations:
- target: 2026-05-24-claim-attention-quadratic
  type: extends
---

On WMT 2014 English-to-German, the Transformer base model achieves 27.3 BLEU, surpassing the prior best ensemble result while training in a fraction of the wall-clock time.