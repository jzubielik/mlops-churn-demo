# Build plan (milestone by milestone)

Each milestone = one commit, leaving the repo in a working state.
Messages follow the Conventional Commits convention (see `../COMMITS.txt`).

| # | Scope | Verification | Commit |
|---|--------|-------------|--------|
| m01 | Init + scaffold (pyproject, Makefile, README, .gitignore, LICENSE, PLAN) | `make test` | `chore: initialize ...` |
| m02 | Data + DVC (ingest/sampling Telco churn, versioning) | `make data && dvc repro` | `feat(data): ...` |
| m03 | Package + feature engineering + tests | `make test && make lint` | `feat(model): ...` |
| m04 | ETL (Prefect) + contract (Pandera), fail-fast on bad data | `make etl` / `make etl-bad` | `feat(pipeline): ...` |
| m05 | MLflow tracking + registry + promotion by PR-AUC | `make train && make promote` | `feat(experiments): ...` |
| m06 | Quality gate (PR-AUC) + CI (lint/test/train/gate) | `make ci` | `ci: ...` |
| m07 | FastAPI serving + Docker + load test + /metrics | serve + curl + loadtest | `feat(serving): ...` |
| m08 | Monitoring (Prometheus/Grafana) + drift (Evidently) | `make monitor-up` / `make drift` | `feat(monitoring): ...` |
| m09 | Terraform infra (local providers) | `terraform apply/destroy` | `feat(infra): ...` |
| m10 | Security: Vault + Trivy/Gitleaks | vault flow + `make scan` | `feat(security): ...` |
| m11 | Model/data cards + GitHub Pages with reports | site build | `docs: ...` |
| m12 | Scheduled retrain (cron) + PR comment/artifact | YAML validation | `ci: ...` |
| m13 | End-to-end README + diagram + `make demo` | `make demo` | `docs: ...` |

## Principles
- Snapshots are built strictly in order and cumulatively (mN+1 = mN + delta).
- Artifacts (`.venv`, `mlruns/`, `build/`, `*.tfstate`, ...) are not committed to the repo.
- Dataset: Telco Customer Churn — imbalanced, a realistic KPI, easy to drift.
- Goal: the whole flow runnable locally and verifiable on a free GH runner.
