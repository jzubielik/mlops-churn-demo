# MLOps Churn Demo — helper targets (developed milestone by milestone).

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
DVC  := $(VENV)/bin/dvc

REMOTE_DIR := ./dvcstore

# dvc.yaml stages call bare `python` — we prepend .venv/bin to PATH.
export PATH := $(CURDIR)/$(VENV)/bin:$(PATH)

# Prefect should run 100% locally and quietly (no server/telemetry).
export PREFECT_HOME          := $(CURDIR)/.prefect
export PREFECT_LOGGING_LEVEL := INFO
export PREFECT_CLI_COLORS    := false

# MLflow: a consistent backend (ABSOLUTE path) for scripts and the UI.
MLFLOW := $(VENV)/bin/mlflow
export MLFLOW_TRACKING_URI := sqlite:///$(CURDIR)/mlflow.db
MLFLOW_PORT ?= 17150

.PHONY: help install patch-py314 test lint clean \
        data init repro metrics etl etl-bad \
        train tune promote mlflow-ui

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Create .venv and install package + dependencies (requirements.txt)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"
	@$(MAKE) --no-print-directory patch-py314

# MLflow compatibility patch for Python 3.14: 'Traversable' was moved from
# importlib.abc to importlib.resources.abc. Without this MLflow won't start.
patch-py314: ## Patch MLflow for Python 3.14
	@f=$$(ls $(VENV)/lib/python3.*/site-packages/mlflow/assistant/skill_installer.py 2>/dev/null); \
	if [ -n "$$f" ] && grep -q '^from importlib\.abc import Traversable' "$$f"; then \
		sed -i 's/^from importlib\.abc import Traversable/from importlib.resources.abc import Traversable/' "$$f"; \
		echo "patch-py314: applied MLflow patch"; \
	else \
		echo "patch-py314: nothing to do (already patched or MLflow not installed)"; \
	fi

test: ## Run tests with coverage
	$(VENV)/bin/pytest --cov=churnml

lint: ## Static code analysis (ruff)
	$(VENV)/bin/ruff check .

# --- m02: data + DVC -------------------------------------------------------
init: ## git init + dvc init + local remote ($(REMOTE_DIR))
	@test -d .git || git init -q
	@git config user.email >/dev/null 2>&1 || git config user.email "demo@local"
	@git config user.name  >/dev/null 2>&1 || git config user.name  "Churn Demo"
	@test -d .dvc || $(DVC) init -q
	$(DVC) remote add -d --force localremote $(REMOTE_DIR)
	@echo "Initialized git + DVC. Remote 'localremote' -> $(REMOTE_DIR)"

data: ## Synthesize data/raw.csv and add it to DVC
	$(PY) scripts/make_data.py
	$(DVC) add data/raw.csv
	@echo "Generated and added data/raw.csv to DVC."

repro: ## Run the DVC pipeline (prepare -> train)
	$(DVC) repro

metrics: ## Show the pipeline metrics (dvc metrics show)
	$(DVC) metrics show

# --- m04: ETL (Prefect) + validation (Pandera) -----------------------------
etl: ## ETL flow on CLEAN data (extract->validate->features->load parquet)
	$(PY) pipelines/etl_flow.py data/raw.csv

etl-bad: ## ETL flow on CORRUPTED data (expected validation failure, exit 1)
	@$(PY) scripts/make_corrupted.py
	@echo ">>> Running ETL on CORRUPTED data — validation should stop the flow..."
	@$(PY) pipelines/etl_flow.py data/raw_corrupted.csv; \
		status=$$?; \
		if [ $$status -ne 0 ]; then \
			echo ">>> OK: flow stopped by validation (exit $$status) — as expected."; \
		else \
			echo ">>> ERROR: flow passed but should have failed!"; exit 1; \
		fi

# --- m05: experiments (MLflow) ---------------------------------------------
train: ## Run MLflow experiments (several models, churn-clf registry)
	$(PY) experiments/run.py

tune: ## Optuna hyperparameter tuning (maximize pr_auc)
	$(PY) experiments/tune_optuna.py

promote: ## Promote the best model (pr_auc) -> alias @production
	$(PY) experiments/promote.py

mlflow-ui: ## MLflow UI at http://localhost:$(MLFLOW_PORT)
	$(MLFLOW) ui --backend-store-uri $(MLFLOW_TRACKING_URI) \
		--default-artifact-root ./mlartifacts --host 0.0.0.0 --port $(MLFLOW_PORT)

clean: ## Remove venv, cache and build artifacts
	rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
