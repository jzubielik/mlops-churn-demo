# MLOps Churn Demo

An end-to-end MLOps demo on a real business problem: **customer churn
prediction** for a telecom operator. The project shows a full, production-grade
ML lifecycle — from versioned data, through tracked training and a quality gate,
to serving, drift monitoring and retraining — entirely **runnable locally** and
verified on a **free GitHub Actions runner**.

> Status: 🚧 under construction (milestone by milestone). See [PLAN.md](PLAN.md).

## Problem

Churn = a customer leaving the service. Task: **binary classification** —
predict which customers will leave so you can act in time (retention). The data
is **imbalanced** (~26% churn), so we measure quality with **PR-AUC / F1**, not accuracy.

Dataset: **Telco Customer Churn** (~7k customers, ~20 features).

## Planned architecture

```
data (DVC) → ETL+validation (Prefect/Pandera) → training+tracking (MLflow)
   → quality gate (PR-AUC) → serving (FastAPI) → monitoring (Prometheus/Grafana)
   → drift (Evidently) → retraining
        all of it: IaC (Terraform) · secrets (Vault) · scans (Trivy/Gitleaks) · CI (GitHub Actions)
```

## Quick start

```bash
make install     # .venv + dependencies (+ MLflow patch for Python 3.14)
make test        # tests (pytest)
make lint        # ruff

# Data + reproducible pipeline (DVC)
make init        # git + dvc init + local remote (./dvcstore)
make data        # synthesize data/raw.csv (~7000 rows, ~26% churn) + dvc add
make repro       # DVC pipeline: prepare -> train (model.joblib + metrics.json)
make metrics     # dvc metrics show

# ETL (Prefect) + data contract (Pandera)
make etl         # extract -> validate -> features -> load (parquet)
make etl-bad     # demo: dirty data stopped by validation (exit 1)

# Experiments (MLflow)
make train       # several models -> churn-clf registry
make tune        # Optuna tuning (pr_auc)
make promote     # best model -> alias @production
make mlflow-ui   # UI: http://localhost:17150

# CI / quality gate (pr_auc)
make ci          # lint -> test -> train -> gate (like GitHub Actions)

# Serving (FastAPI, port 17100)
make train-model # ensure model.joblib
make serve       # uvicorn on :17100  (/health /predict /metrics /docs)
make predict     # example curl request
make loadtest    # p50/p95/p99
make docker-build
```

A full `make demo` (the whole flow in one command) will come in the final milestone.

## Stack

scikit-learn · DVC · MLflow · Prefect · Pandera · FastAPI · Prometheus + Grafana ·
Evidently · Docker · Terraform · Vault · Trivy/Gitleaks · GitHub Actions

## License

MIT — see [LICENSE](LICENSE).
