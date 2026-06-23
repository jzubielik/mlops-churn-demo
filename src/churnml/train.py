"""`train` stage: trains the churn model, computes metrics, saves artifacts.

* `train(...)` -> (model, metrics), metrics: pr_auc, roc_auc, f1, accuracy.
* `main()` -> reads data/processed/{train,test}.csv (from the prepare stage),
  trains according to params.yaml, saves model.joblib + metrics.json.

The model is selected via params.yaml (train.model: "logreg" | "hgb").
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.pipeline import Pipeline

from churnml.data import TARGET
from churnml.evaluate import evaluate
from churnml.model import make_model

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
MODEL = ROOT / "model.joblib"
METRICS = ROOT / "metrics.json"


def _xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    y = (df[TARGET].astype(str).str.strip() == "Yes").astype(int)
    X = df.drop(columns=[c for c in (TARGET, "customerID") if c in df.columns])
    return X, y


def train(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    kind: str = "logreg",
    **model_kwargs,
) -> tuple[Pipeline, dict[str, float]]:
    """Fit the Pipeline and compute metrics on the test set."""
    model = make_model(kind=kind, **model_kwargs)
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    metrics = evaluate(y_test, proba)
    return model, metrics


def main() -> None:
    params = yaml.safe_load((ROOT / "params.yaml").read_text())["train"]
    kind = params.get("model", "logreg")
    model_kwargs = {k: v for k, v in params.items() if k not in ("model", "seed")}

    train_df = pd.read_csv(PROC / "train.csv")
    test_df = pd.read_csv(PROC / "test.csv")
    X_train, y_train = _xy(train_df)
    X_test, y_test = _xy(test_df)

    model, metrics = train(X_train, y_train, X_test, y_test, kind=kind, **model_kwargs)
    metrics["n_train"] = int(len(train_df))
    metrics["n_test"] = int(len(test_df))

    joblib.dump(model, MODEL)
    METRICS.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"train: model -> {MODEL}")
    print(f"train: metrics -> {METRICS}: {metrics}")


if __name__ == "__main__":
    main()
