.PHONY: install seed seed-quick api app museum cli-help test eval clean

PY := .venv/bin/python
PYTHONPATH := .
export PYTHONPATH

install:
	@command -v uv >/dev/null 2>&1 && uv sync || $(PY) -m pip install -e .

# Full seed: scenarios + bundled PDFs + SDG-aligned atoms + scoring datasets.
# Idempotent — safe to re-run.
seed:
	$(PY) scripts/seed_scenarios.py
	$(PY) scripts/seed_papers.py
	@for pdf in data/sources/sdg-briefing-ch*.pdf; do \
		$(PY) -m openacad.cli._legacy_main ingest "$$pdf" || true; \
	done
	$(PY) scripts/seed_sdg_atoms.py
	$(PY) scripts/seed_scoring_datasets.py

# Skip PDF ingestion + atom re-seed (useful when iterating on agent code only).
seed-quick:
	$(PY) scripts/seed_scenarios.py
	$(PY) scripts/seed_scoring_datasets.py

api:
	$(PY) -m uvicorn openacad.server.main:app --reload --host 127.0.0.1 --port 8000

# Frozen 9-rung Streamlit thesis tour (Milestone-5 will move this to optional dep).
museum:
	$(PY) -m streamlit run museum/streamlit/streamlit_app.py --server.port 8585

# `app` was the Streamlit demo entry; kept as an alias to `museum` during the M0-M4 transition.
app: museum

cli-help:
	$(PY) -m openacad.cli --help

test:
	$(PY) -m pytest tests/ -v

eval:
	$(PY) scripts/run_baselines.py
	$(PY) scripts/run_atom.py
	$(PY) scripts/eval_report.py

clean:
	rm -rf data/embeddings/*.npz data/state.json data/state.sqlite*
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
