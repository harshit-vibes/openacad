---
description: Run the openacad meta-evaluator to evolve agent prompts
allowed-tools: Bash
---

Run the meta-evaluator pass and paste its output verbatim:

```bash
openacad evolve $ARGUMENTS
```

If `openacad` is not on PATH:

```bash
PYTHONPATH=. .venv/bin/python -m openacad.cli evolve $ARGUMENTS
```

After the run, summarize:
- which prompts were regenerated,
- which were promoted vs. rejected,
- the win-rate delta on the held-out scoring set.
