# Model Card — Churn Classifier (`churn-clf`)

## Overview
- **Task:** binary classification — predict whether a telecom operator's
  customer will churn (churn = `Yes`/`No`).
- **Registry name:** `churn-clf` (MLflow Model Registry, alias `@production`).
- **Type:** scikit-learn `Pipeline` (feature engineering → preprocessing →
  estimator). Pipeline serialized to `model.joblib`.
- **Input:** raw customer fields (data contract — see `docs/data_card.md`).
- **Output:** `churn_probability` (0..1) + `churn_label` (`Yes`/`No`) relative to
  a configurable threshold (default 0.5).

## Model architecture
1. **Feature engineering** (`churnml.features`, stateless `FunctionTransformer`):
   - `tenure_bucket` — tenure bucket (new / 0-12 / 13-24 / 25-48 / 49-72 mo.),
   - `charges_per_tenure` — TotalCharges / max(tenure, 1),
   - `n_addons` — number of purchased add-on services.
2. **Preprocessing** — one-hot for categorical features, scaling for numeric ones.
3. **Estimator** — linear/tree model selected in experiments (MLflow),
   tuned with Optuna for PR-AUC.

## Metrics and evaluation
- **Primary metric:** **PR-AUC (average precision)** — appropriate for
  **imbalanced** data (~26% positives); accuracy can be misleading.
- Auxiliary: ROC-AUC, F1, accuracy. Current model values in `metrics.json`.
- **Quality gate** (`scripts/gate.py`): the model goes "to production" only when
  `pr_auc > baseline` (`baseline.txt`) — protecting against quality regression.

## Training data
- A synthetic, realistic Telco Customer Churn dataset (`scripts/make_data.py`,
  deterministic seed). Details: `docs/data_card.md`.

## Intended use and limitations
- **Intended use:** demonstration of a production MLOps workflow; support for
  retention efforts (prioritizing high-risk customers).
- **Out of scope:** fully automated decisions without human oversight.
- **Limitations:** the data is **synthetic** — the model is not suitable for real
  business decisions without retraining on production data.
- **Risks / fairness:** demographic features (gender, SeniorCitizen, Partner,
  Dependents) would require a bias audit before production use.

## Monitoring and maintenance
- **Data drift:** Evidently (`monitoring/drift_check.py`) compares the reference
  cohort with the current one; a share of drifted features above the threshold
  triggers retraining.
- **Runtime metrics:** Prometheus/Grafana (QPS, p99 latency, drift gauge).
- **Retraining:** automated (scheduled workflow `retrain.yml`).
