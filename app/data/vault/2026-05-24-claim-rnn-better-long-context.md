---
type: claim
created_at: '2026-05-24T11:08:34+00:00'
updated_at: '2026-05-24T11:08:34+00:00'
status: active
tags:
- claim
- nlp
- rnn
- long-context
domain.primary: machine-learning
domain.sub: nlp
evidence.confidence: low
evidence.type: anecdotal
modality.length-regime: ">8192 tokens"
relations:
- type: contradicts
  target: "[[2026-05-24-claim-attention-quadratic]]"
---

Some practitioners report that RNNs handle very long contexts (>8K tokens) more efficiently than vanilla attention, since RNN memory cost is linear in sequence length. The claim is folk knowledge — the supporting evidence is thin and the comparison usually ignores effective context utilisation.

See also: [[2026-05-24-claim-attention-quadratic]]
