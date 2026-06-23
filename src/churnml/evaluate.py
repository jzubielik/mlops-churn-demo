"""Evaluation metrics for the churn model.

The project's key metric: **pr_auc** (average_precision) — appropriate for
imbalanced binary classification. We also compute roc_auc, f1, accuracy.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    roc_auc_score,
)


def evaluate(y_true, y_proba, threshold: float = 0.5) -> dict[str, float]:
    """Compute metrics based on positive-class probabilities.

    Args:
        y_true: true labels (0/1).
        y_proba: probability of class 1 (churn).
        threshold: decision threshold for hard metrics (f1, accuracy).
    """
    y_proba = np.asarray(y_proba, dtype=float)
    y_pred = (y_proba >= threshold).astype(int)
    return {
        "pr_auc": round(float(average_precision_score(y_true, y_proba)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_proba)), 4),
        "f1": round(float(f1_score(y_true, y_pred)), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
    }
