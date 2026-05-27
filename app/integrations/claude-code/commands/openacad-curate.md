---
description: Open the openacad draft-atom curation loop
allowed-tools: Bash
---

Run the openacad curation loop and paste the output verbatim:

```bash
openacad curate $ARGUMENTS
```

If `openacad` is not on PATH:

```bash
PYTHONPATH=. .venv/bin/python -m openacad.cli curate $ARGUMENTS
```

Then, for each pending draft:

1. Show its `body`, `type`, and source span.
2. Recommend one of: **accept**, **edit**, **reject**, with a one-sentence rationale.

Do not call `accept` on the user's behalf — the curation loop is HITL.
