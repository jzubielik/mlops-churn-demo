"""Runs several churn experiments and logs them to MLflow.

Each run logs parameters, metrics (pr_auc, roc_auc, f1, accuracy), and the model.
The model is registered in the Model Registry under the name ``churn-clf``. We
train a mix of logistic regression (various C) and HistGradientBoosting — so that
promotion by pr_auc has a real choice and a sensible tie-break.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mlflow
import mlflow.sklearn

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import MODEL_NAME, setup_mlflow  # noqa: E402

from churnml.data import load_data  # noqa: E402
from churnml.evaluate import evaluate  # noqa: E402
from churnml.model import make_model  # noqa: E402

# (kind, params, "complexity" — lower = simpler/faster model for the tie-break).
CONFIGS = [
    ("logreg", {"C": 0.1}, 1),
    ("logreg", {"C": 1.0}, 1),
    ("logreg", {"C": 10.0}, 1),
    ("hgb", {"max_iter": 150, "learning_rate": 0.1}, 3),
    ("hgb", {"max_iter": 300, "learning_rate": 0.05}, 3),
]


def main() -> None:
    tracking_uri = setup_mlflow()
    print(f"MLFLOW_TRACKING_URI = {tracking_uri}")

    X_train, X_test, y_train, y_test = load_data()

    for i, (kind, params, complexity) in enumerate(CONFIGS, start=1):
        run_name = f"{kind}_" + "_".join(f"{k}{v}" for k, v in params.items())
        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("kind", kind)
            mlflow.log_param("complexity", complexity)
            mlflow.log_params(params)

            model = make_model(kind=kind, **params)
            model.fit(X_train, y_train)
            proba = model.predict_proba(X_test)[:, 1]
            metrics = evaluate(y_test, proba)
            mlflow.log_metrics(metrics)

            mlflow.sklearn.log_model(
                sk_model=model,
                name="model",
                input_example=X_train.head(3),
                registered_model_name=MODEL_NAME,
                # cloudpickle: the pipeline contains a custom FunctionTransformer (engineer).
                serialization_format="cloudpickle",
            )
            print(
                f"  [{i}] {run_name}: pr_auc={metrics['pr_auc']:.4f} "
                f"roc_auc={metrics['roc_auc']:.4f}"
            )

    print(f"\nCompleted {len(CONFIGS)} runs. Promotion: make promote")


if __name__ == "__main__":
    main()
