# MLOps Churn Demo — helper targets.
# Further targets (data/train/serve/monitor/...) are added in the next milestones.

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: help install test lint clean

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create .venv and install the package with dev dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test: ## Run tests with coverage
	$(VENV)/bin/pytest --cov=churnml

lint: ## Static code analysis (ruff)
	$(VENV)/bin/ruff check .

clean: ## Remove venv, cache and build artifacts
	rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
