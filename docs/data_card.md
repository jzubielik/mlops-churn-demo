# Data Card — Telco Customer Churn (synthetic)

## Provenance
- **Source:** data **generated synthetically** by `scripts/make_data.py`
  (deterministic `numpy` seed → reproducible `dvc repro`). **We fetch nothing
  from the network** — everything runs offline, including on the free CI runner.
- **Versioning:** `data/raw.csv` tracked by **DVC** (`data/raw.csv.dvc`),
  local remote `./dvcstore`.
- **Size:** ~7032 rows, ~20 features + label.

## Label
- `Churn` ∈ {`Yes`, `No`}; encoded as 1/0 (1 = churned).
- **Distribution:** imbalanced, ~26% positives → **PR-AUC** metric.

## Feature schema (data contract)
| Column | Type | Description |
|---|---|---|
| `customerID` | str | identifier (dropped from features) |
| `gender` | cat. | Female / Male |
| `SeniorCitizen` | int 0/1 | senior |
| `Partner`, `Dependents` | cat. | Yes / No |
| `tenure` | int 0..72 | tenure in months |
| `PhoneService`, `MultipleLines` | cat. | voice services |
| `InternetService` | cat. | DSL / Fiber optic / No |
| `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` | cat. | add-on services |
| `Contract` | cat. | Month-to-month / One year / Two year |
| `PaperlessBilling` | cat. | Yes / No |
| `PaymentMethod` | cat. | payment method |
| `MonthlyCharges` | float | monthly charge |
| `TotalCharges` | float | total charges |
| `Churn` | cat. | **label** |

## Quality validation
- **Pandera** (`pipelines/schema.py`) enforces the contract in the ETL (Prefect):
  ranges, allowed categories, no nulls in key fields.
- **Fail-fast:** dirty data halts the flow (demo: `make etl-bad`).

## Business correlations (built into the generator)
Higher churn likelihood: *Month-to-month* contract, low `tenure`, high
`MonthlyCharges`, *Fiber optic*, *Electronic check*, missing `TechSupport`/`OnlineSecurity`.

## Drift
- `scripts/make_drifted.py` creates a reference cohort (`data/reference.csv`)
  and a "future" one with injected drift (`data/current.csv`): shorter tenure,
  higher charges, over-weighted risky categories — reliably detectable by
  Evidently (`dataset_drift=True`).

## Ethical notes
- The data is **synthetic** — no real individuals. When using production data,
  one would need to account for GDPR/PII and audit bias of demographic features.
