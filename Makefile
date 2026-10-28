PYTHON ?= .venv/bin/python
UV ?= uv
UV_CACHE_DIR ?= /tmp/campusclaw-uv-cache
OPENSPEC ?= openspec

.PHONY: setup run test lint compile secret-scan layout spec-check check

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) venv .venv --python 3.12 --allow-existing
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) pip install --python $(PYTHON) -r requirements-dev.lock
	git config core.hooksPath .githooks || echo "warning: git config is read-only; enable .githooks manually"

run:
	$(PYTHON) -m gunicorn --config gunicorn.conf.py 'campusclaw:create_app()'

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

compile:
	$(PYTHON) -m compileall -q campusclaw tests scripts

secret-scan:
	$(PYTHON) scripts/secret_scan.py

layout:
	$(PYTHON) scripts/check_layout.py

spec-check:
	$(PYTHON) scripts/validate_change.py
	$(OPENSPEC) validate --changes --strict --no-interactive
	$(OPENSPEC) validate --archived --strict --no-interactive

check: lint compile test layout secret-scan spec-check
