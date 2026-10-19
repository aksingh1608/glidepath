PY := .venv/bin/python

.PHONY: install status synthetic test results results-synthetic docs serve

install:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

status:
	python3 collect_live.py --status

synthetic:
	$(PY) -m pipeline.synthetic --out data/synthetic

test:
	$(PY) -m pytest -q tests

results:
	$(PY) run.py --raw data/raw/live

results-synthetic: synthetic
	$(PY) run.py --raw data/synthetic --synthetic

docs:
	$(PY) run.py --docs-only

serve:
	$(PY) -m http.server 8000 --directory web
