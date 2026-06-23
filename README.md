# MLOps Churn Demo

End-to-end MLOps demo on a real business problem: **customer churn
prediction** for a telecom operator. The project demonstrates a complete,
production-grade ML lifecycle — from versioned data, through tracked training and a
quality gate, to serving, drift monitoring and retraining — all **runnable
locally** and verified on a **free GitHub Actions runner**.

> Status: 🚧 under construction (milestone by milestone). See [PLAN.md](PLAN.md).

## Problem

Churn = a customer leaving the service. Task: **binary classification** —
predict which customers will leave so you can act in time (retention). The data is
**imbalanced** (~26% churn), so we measure quality with **PR-AUC / F1**, not accuracy.

Dataset: **Telco Customer Churn** (~7k customers, ~20 features).

## Planned architecture

```
data (DVC) → ETL+validation (Prefect/Pandera) → training+tracking (MLflow)
   → quality gate (PR-AUC) → serving (FastAPI) → monitoring (Prometheus/Grafana)
   → drift (Evidently) → retraining
        overall: IaC (Terraform) · secrets (Vault) · scans (Trivy/Gitleaks) · CI (GitHub Actions)
```

## Quick start

```bash
make install     # environment + dependencies
make test        # tests + lint
```

The full `make demo` (the entire flow in one command) will arrive in the final milestone.

## Stack

scikit-learn · DVC · MLflow · Prefect · Pandera · FastAPI · Prometheus + Grafana ·
Evidently · Docker · Terraform · Vault · Trivy/Gitleaks · GitHub Actions

## License

MIT — see [LICENSE](LICENSE).
