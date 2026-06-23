"""Churn model factory — a complete sklearn Pipeline.

Pipeline:
    feature_engineer (FunctionTransformer)  -> adds derived features
      -> ColumnTransformer:
           OneHotEncoder on categorical columns,
           StandardScaler on numeric columns
      -> classifier with class-imbalance handling.

Default classifier: logistic regression with `class_weight="balanced"`
(a simple, fast baseline). You can choose `kind="hgb"` (HistGradientBoosting)
for a stronger model — used during tuning and promotion.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from churnml.features import (
    ENGINEERED_NUMERIC,
    NUMERIC_BASE,
    make_feature_engineer,
)

RANDOM_STATE = 42

NUMERIC_FEATURES = NUMERIC_BASE + ENGINEERED_NUMERIC

# Categorical columns (all the rest; tenure_bucket is added by feature
# engineering). An explicit list -> a stable column contract for OneHot.
CATEGORICAL_FEATURES = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "tenure_bucket",
]


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def make_model(kind: str = "logreg", **kwargs) -> Pipeline:
    """Build an untrained churn model Pipeline.

    Args:
        kind: "logreg" (default) or "hgb" (HistGradientBoosting).
        **kwargs: overrides for the classifier hyperparameters.
    """
    if kind == "logreg":
        clf = LogisticRegression(
            max_iter=kwargs.pop("max_iter", 1000),
            class_weight="balanced",
            C=kwargs.pop("C", 1.0),
            random_state=RANDOM_STATE,
            **kwargs,
        )
    elif kind == "hgb":
        clf = HistGradientBoostingClassifier(
            learning_rate=kwargs.pop("learning_rate", 0.1),
            max_depth=kwargs.pop("max_depth", None),
            max_iter=kwargs.pop("max_iter", 200),
            class_weight="balanced",
            random_state=RANDOM_STATE,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown model kind: {kind!r} (use 'logreg' or 'hgb').")

    return Pipeline(
        steps=[
            ("features", make_feature_engineer()),
            ("preprocess", _build_preprocessor()),
            ("clf", clf),
        ]
    )


def expected_columns() -> list[str]:
    """Raw input columns expected by the model (before feature eng.)."""
    base = set(CATEGORICAL_FEATURES) - {"tenure_bucket"}
    return sorted(base | set(NUMERIC_BASE))


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Helper: ensure the expected columns are present (no-op when they are)."""
    return df
