PYTHON ?= .venv/bin/python
UV ?= uv
UV_CACHE_DIR ?= /tmp/campusclaw-uv-cache

.PHONY: setup run test lint compile secret-scan layout spec-check check check-security dependency-audit

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) venv .venv --python 3.12 --allow-existing
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) pip install --python $(PYTHON) -r requirements-dev.lock
	git config core.hooksPath .githooks || echo "warning: git config is read-only; enable .githooks manually"

run:
	$(PYTHON) -m flask --app 'campusclaw:create_app()' run --host 127.0.0.1 --port 5000

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

compile:
	$(PYTHON) -m compileall -q campusclaw tests scripts apitest conftest.py

secret-scan:
	$(PYTHON) scripts/secret_scan.py

layout:
	$(PYTHON) scripts/check_layout.py

spec-check:
	$(PYTHON) scripts/validate_change.py

check: lint compile test layout secret-scan spec-check

# Security gate: every component must run; a failure cannot be hidden by another success.
SECURITY_ROOT ?= .
dependency-audit:
	$(PYTHON) scripts/dependency_audit.py --root "$(SECURITY_ROOT)" --output reports/evidence/dependencies-current.json

check-security:
	@result=0; $(PYTHON) scripts/secret_scan.py --root "$(SECURITY_ROOT)" || result=1; \
	$(PYTHON) scripts/dependency_audit.py --root "$(SECURITY_ROOT)" --output reports/evidence/dependencies-current.json || result=1; \
	exit $$result
