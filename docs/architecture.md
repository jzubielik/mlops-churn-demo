# Architecture — MLOps Churn Demo

A full, production-grade ML workflow for churn prediction, runnable locally and on
the free GitHub Actions runner. Each stage maps to an element of the MLOps
lifecycle.

## Flow diagram

```mermaid
%%{init: {"theme":"base", "themeVariables":{"fontSize":"24px"}, "flowchart": {"htmlLabels": true, "nodeSpacing": 35, "rankSpacing": 65, "padding": 20, "subGraphTitleMargin": {"top": 14, "bottom": 14}, "curve": "basis"}}}%%
flowchart TB
    subgraph DATA["1 · Data &amp; versioning"]
        direction LR
        MK["make_data.py<br/>Telco synthesis"] --> RAW["data/raw.csv<br/>(DVC)"] --> ETL["ETL · Prefect<br/>validate→load"] -->|Pandera| PARQ["data/processed<br/>(parquet)"]
    end

    subgraph TRAIN["2 · Training &amp; experiments"]
        direction LR
        PREP["prepare<br/>train/test split"] --> TR["train<br/>sklearn Pipeline"] --> MLF["MLflow + Optuna<br/>registry"] --> PROMO["promote<br/>@production"]
        TR --> MODEL["model.joblib<br/>+ metrics.json"]
    end

    subgraph GATE["3 · Quality gate &amp; CI"]
        direction LR
        CI["CI · lint→test<br/>→train→gate"] --> G{"gate.py<br/>pr_auc > baseline?"}
        G -->|yes| OK["deploy allowed"]
        G -->|no| STOP["pipeline FAIL"]
    end

    subgraph SERVE["4 · Serving &amp; monitoring"]
        direction LR
        VAULT["Vault :17200"] -->|startup| APP["FastAPI :17100<br/>/predict /metrics"] --> PROM["Prometheus<br/>:17190"] --> GRAF["Grafana :17130<br/>QPS · p99 · drift"]
    end

    subgraph MON["5 · Drift &amp; retrain"]
        direction LR
        DRIFT["Evidently<br/>drift_check"] -->|drift > thr| RETR["retrain<br/>+ gate"]
        DRIFT --> RPT["drift_report.html"]
        CRON["retrain.yml<br/>(cron)"] --> DRIFT
    end

    subgraph OPS["6 · Platform &amp; reports"]
        direction LR
        INFRA["Terraform infra/<br/>Trivy · Gitleaks"]
        PAGES["Report site<br/>(Pages)"]
    end

    RAW --> PREP
    MODEL --> G
    OK --> APP
    APP -.->|/drift-score| DRIFT
    RETR -.-> MODEL
    MODEL --> PAGES
    RPT --> PAGES

    classDef data fill:#dbeafe,stroke:#3b82f6,stroke-width:2px;
    classDef train fill:#dcfce7,stroke:#16a34a,stroke-width:2px;
    classDef gate fill:#fef08a,stroke:#ca8a04,stroke-width:2px;
    classDef serve fill:#fae8ff,stroke:#a21caf,stroke-width:2px;
    classDef ops fill:#e2e8f0,stroke:#64748b,stroke-width:2px;
    class MK,RAW,ETL,PARQ data;
    class PREP,TR,MLF,PROMO,MODEL train;
    class CI,G,OK,STOP gate;
    class VAULT,APP,PROM,GRAF serve;
    class DRIFT,RETR,RPT,CRON serve;
    class INFRA,PAGES ops;
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
