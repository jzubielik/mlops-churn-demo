"""Churn hyperparameter tuning with Optuna (maximizing pr_auc).

Each trial is logged as a nested run under the parent run 'optuna-study'.
Optuna tunes a HistGradientBoostingClassifier. The best trial registers its
model in the Model Registry (ready for promotion).
"""

from __future__ import annotations

import sys
from pathlib import Path

import mlflow
import mlflow.sklearn
import optuna

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import MODEL_NAME, setup_mlflow  # noqa: E402

from churnml.data import load_data  # noqa: E402
from churnml.evaluate import evaluate  # noqa: E402
from churnml.model import make_model  # noqa: E402

N_TRIALS = 12


def main() -> None:
    tracking_uri = setup_mlflow()
    print(f"MLFLOW_TRACKING_URI = {tracking_uri}")

    X_train, X_test, y_train, y_test = load_data()

    def objective(trial: optuna.Trial) -> float:
        params = {
            "max_iter": trial.suggest_int("max_iter", 100, 400, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
        }
        with mlflow.start_run(run_name=f"optuna-trial-{trial.number}", nested=True):
            mlflow.log_param("kind", "hgb")
            mlflow.log_param("complexity", 3)
            mlflow.log_params(params)
            model = make_model(kind="hgb", **params)
            model.fit(X_train, y_train)
            proba = model.predict_proba(X_test)[:, 1]
            metrics = evaluate(y_test, proba)
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(
                sk_model=model,
                name="model",
                registered_model_name=MODEL_NAME,
                serialization_format="cloudpickle",
            )
            return metrics["pr_auc"]

    with mlflow.start_run(run_name="optuna-study"):
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=N_TRIALS)
        mlflow.log_params({f"best_{k}": v for k, v in study.best_params.items()})
        mlflow.log_metric("best_pr_auc", study.best_value)
        print(f"\nBest pr_auc: {study.best_value:.4f}")
        print(f"Best parameters: {study.best_params}")
        print("Promote the best model: make promote")


if __name__ == "__main__":
    main()
