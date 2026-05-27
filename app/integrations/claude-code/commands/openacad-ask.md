---
description: Ask a question against the openacad vault
allowed-tools: Bash
---

Run the following shell command and paste its output verbatim:

```bash
openacad ask "$ARGUMENTS"
```

If `openacad` is not on PATH, fall back to:

```bash
PYTHONPATH=. .venv/bin/python -m openacad.cli ask "$ARGUMENTS"
```

After printing the answer, briefly summarize:
- the top atoms cited (by id), and
- whether the answer used semantic or full-text retrieval.
