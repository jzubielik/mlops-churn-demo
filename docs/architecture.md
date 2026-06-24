# Architecture — MLOps Churn Demo

A full, production-grade ML workflow for churn prediction, runnable locally and on
the free GitHub Actions runner. Each stage maps to an element of the MLOps
lifecycle.

## Flow diagram

```mermaid
flowchart TD
    subgraph DATA["Data and versioning"]
        MK["scripts/make_data.py · Telco churn synthesis"] --> RAW["data/raw.csv · (DVC)"]
        RAW --> ETL["ETL — Prefect · extract→validate→features→load"]
        ETL -->|Pandera contract| PARQ["data/processed · (parquet)"]
    end

    subgraph TRAIN["Training and experiments"]
        RAW --> PREP["churnml.prepare · train/test split"]
        PREP --> TR["churnml.train · sklearn Pipeline"]
        TR --> MLF["MLflow tracking · + churn-clf registry"]
        MLF --> OPT["Optuna tuning (PR-AUC)"]
        OPT --> PROMO["promote → alias @production"]
        TR --> MODEL["model.joblib · + metrics.json"]
    end

    subgraph GATE["Quality gate and CI"]
        MODEL --> G["scripts/gate.py · pr_auc > baseline?"]
        G -->|yes| OK["deploy allowed"]
        G -->|no| STOP["pipeline FAIL"]
        CI["CI: lint→test→train→gate→build"] --> G
    end

    subgraph SERVE["Serving"]
        MODEL --> APP["FastAPI :17100 · /predict /health /metrics /drift-score"]
        VAULT["Vault :17200 · (api_token secret)"] -->|startup| APP
    end

    subgraph MON["Monitoring and drift"]
        APP -->|/metrics| PROM["Prometheus :17190"]
        PROM --> GRAF["Grafana :17130 · QPS · p99 · drift gauge"]
        DRIFT["Evidently drift_check · reference vs current"] -->|/drift-score| APP
        DRIFT --> RPT["drift_report.html"]
        DRIFT -->|drift > threshold| RETR["retrain · train-model + gate"]
    end

    subgraph OPS["Platform and ops"]
        TF["Terraform infra/ · bucket · registry · env-config"]
        SCAN["Trivy + Gitleaks · (security CI)"]
        PAGES["Report site · (Pages / artifact)"]
        CRON["retrain.yml (cron)"]
    end

    RETR --> MODEL
    MODEL --> PAGES
    RPT --> PAGES
    CRON --> DRIFT
```

## Mapping to the MLOps lifecycle

| Phase | Component | Files |
|---|---|---|
| Data / versioning | DVC + synthesis | `scripts/make_data.py`, `dvc.yaml`, `data/raw.csv.dvc` |
| Data validation | Prefect + Pandera | `pipelines/etl_flow.py`, `pipelines/schema.py` |
| Training / experiments | sklearn + MLflow + Optuna | `src/churnml/`, `experiments/` |
| Quality gate | metric gate (PR-AUC) | `scripts/gate.py`, `baseline.txt` |
| CI/CD | GitHub Actions | `.github/workflows/ci.yml` |
| Serving | FastAPI + Docker | `serving/app.py`, `serving/Dockerfile` |
| Monitoring | Prometheus + Grafana | `monitoring/` |
| Drift / retraining | Evidently | `monitoring/drift_check.py`, `scripts/make_drifted.py` |
| Infrastructure (IaC) | Terraform | `infra/` |
| Security | Vault + Trivy + Gitleaks | `security/`, `serving/vault.py`, `.github/workflows/security.yml` |
| Reports / Pages | static site | `scripts/build_site.py`, `.github/workflows/pages.yml` |
| Automation | scheduled retrain | `.github/workflows/retrain.yml` |

## Ports (host)
- Service: **17100** · Prometheus: **17190** · Grafana: **17130** · Vault: **17200** · MLflow UI: **17150**
