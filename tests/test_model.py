"""Tests for the churn model and training — including the pr_auc floor."""

import pytest

from churnml.data import load_data
from churnml.evaluate import evaluate
from churnml.model import make_model
from churnml.train import train

PR_AUC_FLOOR = 0.55


@pytest.fixture(scope="module")
def split():
    return load_data()


def test_make_model_is_pipeline_with_predict_proba() -> None:
    model = make_model()
    # The Pipeline has 3 steps: features -> preprocess -> clf.
    assert [name for name, _ in model.steps] == ["features", "preprocess", "clf"]
    assert hasattr(model, "predict_proba")


def test_make_model_hgb_variant() -> None:
    model = make_model(kind="hgb")
    assert model.steps[-1][0] == "clf"


def test_make_model_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        make_model(kind="nope")


def test_train_returns_model_and_required_metrics(split) -> None:
    X_train, X_test, y_train, y_test = split
    model, metrics = train(X_train, y_train, X_test, y_test)
    assert model is not None
    assert {"pr_auc", "roc_auc", "f1", "accuracy"} <= set(metrics)


def test_train_pr_auc_above_floor(split) -> None:
    X_train, X_test, y_train, y_test = split
    _, metrics = train(X_train, y_train, X_test, y_test)
    # Imbalanced data: pr_auc must clearly beat the baseline (= churn rate).
    assert metrics["pr_auc"] > PR_AUC_FLOOR


def test_evaluate_perfect_scores() -> None:
    y_true = [0, 0, 1, 1]
    y_proba = [0.01, 0.2, 0.8, 0.99]
    m = evaluate(y_true, y_proba)
    assert m["pr_auc"] == 1.0
    assert m["roc_auc"] == 1.0
