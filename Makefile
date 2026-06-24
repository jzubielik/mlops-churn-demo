# MLOps Churn Demo — helper targets (expanded milestone by milestone).

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
DVC  := $(VENV)/bin/dvc

REMOTE_DIR := ./dvcstore

# dvc.yaml stages call bare `python` — we prepend .venv/bin to PATH.
export PATH := $(CURDIR)/$(VENV)/bin:$(PATH)

# Prefect must run 100% locally and quietly (no server/telemetry).
export PREFECT_HOME          := $(CURDIR)/.prefect
export PREFECT_LOGGING_LEVEL := INFO
export PREFECT_CLI_COLORS    := false

# MLflow: consistent backend (ABSOLUTE path) for scripts and UI.
MLFLOW := $(VENV)/bin/mlflow
export MLFLOW_TRACKING_URI := sqlite:///$(CURDIR)/mlflow.db
MLFLOW_PORT ?= 17150

SERVE_PORT ?= 17100
SERVE_URL  ?= http://localhost:$(SERVE_PORT)
IMAGE      ?= churnml-serving:latest

COMPOSE_MON := monitoring/docker-compose.yml

.PHONY: help install patch-py314 test lint clean \
        data init repro metrics etl etl-bad \
        train tune promote mlflow-ui \
        train-model gate ci \
        serve predict loadtest docker-build \
        monitor-up monitor-down gen-drift drift \
        infra-init infra-plan infra-apply infra-output infra-destroy

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
patch-py314: ## MLflow patch for Python 3.14
	@f=$$(ls $(VENV)/lib/python3.*/site-packages/mlflow/assistant/skill_installer.py 2>/dev/null); \
	if [ -n "$$f" ] && grep -q '^from importlib\.abc import Traversable' "$$f"; then \
		sed -i 's/^from importlib\.abc import Traversable/from importlib.resources.abc import Traversable/' "$$f"; \
		echo "patch-py314: applied MLflow patch"; \
	else \
		echo "patch-py314: nothing to do (already patched or MLflow missing)"; \
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

metrics: ## Show pipeline metrics (dvc metrics show)
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
			echo ">>> OK: flow stopped by validation (exit $$status) — as intended."; \
		else \
			echo ">>> ERROR: flow passed, but it should have failed!"; exit 1; \
		fi

# --- m05: experiments (MLflow) ---------------------------------------------
train: ## Run MLflow experiments (several models, churn-clf registry)
	$(PY) experiments/run.py

tune: ## Optuna hyperparameter tuning (maximize pr_auc)
	$(PY) experiments/tune_optuna.py

promote: ## Promote the best model (pr_auc) -> alias @production
	$(PY) experiments/promote.py

mlflow-ui: ## MLflow UI na http://localhost:$(MLFLOW_PORT)
	$(MLFLOW) ui --backend-store-uri $(MLFLOW_TRACKING_URI) \
		--default-artifact-root ./mlartifacts --host 0.0.0.0 --port $(MLFLOW_PORT)

# --- m06: quality gate + CI ------------------------------------------------
train-model: ## Synthesize data and train a single model -> model.joblib + metrics.json
	$(PY) scripts/make_data.py
	$(PY) -m churnml.prepare
	$(PY) -m churnml.train

gate: ## Quality gate: blocks when pr_auc <= baseline.txt
	$(PY) scripts/gate.py --no-promote

ci: lint test train-model gate ## Full pipeline LOCALLY (like GitHub Actions)
	@echo "[CI] Pipeline OK — model passed the pr_auc gate."

# --- m07: serving (FastAPI) ------------------------------------------------
serve: ## Run the FastAPI service (uvicorn) on port $(SERVE_PORT)
	$(VENV)/bin/uvicorn serving.app:app --host 0.0.0.0 --port $(SERVE_PORT)

predict: ## Example request to /predict (curl)
	curl -s -X POST $(SERVE_URL)/predict \
		-H "Content-Type: application/json" \
		-d '{"gender":"Female","SeniorCitizen":0,"Partner":"Yes","Dependents":"No","tenure":2,"PhoneService":"Yes","MultipleLines":"No","InternetService":"Fiber optic","OnlineSecurity":"No","OnlineBackup":"No","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check","MonthlyCharges":89.5,"TotalCharges":179.0}'
	@echo

loadtest: ## Load test for /predict (p50/p95/p99)
	$(PY) serving/load_test.py --url $(SERVE_URL)/predict -n 2000 -c 50

docker-build: ## Build the multi-stage service image
	docker build -t $(IMAGE) -f serving/Dockerfile .

# --- m08: monitoring (Prometheus + Grafana) + drift (Evidently) ------------
monitor-up: ## Bring up the monitoring stack (service + Prometheus :17190 + Grafana :17130)
	docker compose -f $(COMPOSE_MON) up -d --build
	@echo "Prometheus: http://localhost:17190  |  Grafana: http://localhost:17130 (admin/admin)"

monitor-down: ## Stop and remove the monitoring stack
	docker compose -f $(COMPOSE_MON) down -v

gen-drift: ## Generate cohorts data/reference.csv + data/current.csv (with drift)
	$(PY) scripts/make_drifted.py

drift: ## Drift report (Evidently): HTML + push gauge + retrain when > threshold
	$(PY) monitoring/drift_check.py

# --- m09: Infrastructure as Code (Terraform, local) ------------------------
TF      ?= terraform
INFRADIR := infra

infra-init: ## terraform init (infra/ directory)
	cd $(INFRADIR) && $(TF) init

infra-plan: ## terraform plan (shows what will be created under infra/build/)
	cd $(INFRADIR) && $(TF) fmt -check && $(TF) validate && $(TF) plan

infra-apply: ## terraform apply -auto-approve (creates churn platform files)
	cd $(INFRADIR) && $(TF) apply -auto-approve

infra-output: ## terraform output (platform names/paths)
	cd $(INFRADIR) && $(TF) output

infra-destroy: ## terraform destroy -auto-approve (cleans up infra/build/)
	cd $(INFRADIR) && $(TF) destroy -auto-approve

clean: ## Remove venv, caches and build artifacts
	rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
