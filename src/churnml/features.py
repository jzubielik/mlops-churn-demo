"""Feature engineering for churn — used inside the model pipeline.

The transforms are stateless (purely row-wise), so we wrap them in a
`FunctionTransformer` to make them behave consistently in training and serving:

* tenure_bucket   — tenure bucket (0, 1-12, 13-24, 25-48, 49-72 months),
* charges_per_tenure — TotalCharges / tenure (spending intensity),
* n_addons        — number of purchased add-on services.

The `engineer()` function takes and returns a DataFrame; `make_feature_engineer()`
returns a ready `FunctionTransformer` to put at the start of the Pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import FunctionTransformer

ADDON_COLS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "MultipleLines",
]

NUMERIC_BASE = ["tenure", "MonthlyCharges", "TotalCharges"]
ENGINEERED_NUMERIC = ["charges_per_tenure", "n_addons"]


def _tenure_bucket(tenure: pd.Series) -> pd.Series:
    bins = [-1, 0, 12, 24, 48, 72]
    labels = ["new", "0-12", "13-24", "25-48", "49-72"]
    return pd.cut(tenure, bins=bins, labels=labels).astype(str)


def engineer(X: pd.DataFrame) -> pd.DataFrame:
    """Add derived features (returns a new frame)."""
    out = X.copy()

    # TotalCharges may arrive as text (empty values) — coerce to numeric.
    out["TotalCharges"] = pd.to_numeric(out["TotalCharges"], errors="coerce").fillna(0.0)
    out["MonthlyCharges"] = pd.to_numeric(out["MonthlyCharges"], errors="coerce").fillna(0.0)
    out["tenure"] = pd.to_numeric(out["tenure"], errors="coerce").fillna(0).astype(int)

    out["tenure_bucket"] = _tenure_bucket(out["tenure"])
    out["charges_per_tenure"] = out["TotalCharges"] / np.maximum(out["tenure"], 1)
    out["n_addons"] = sum((out[c] == "Yes").astype(int) for c in ADDON_COLS if c in out.columns)

    return out


def make_feature_engineer() -> FunctionTransformer:
    """`FunctionTransformer` wrapping `engineer` (pandas in/out)."""
    return FunctionTransformer(engineer, validate=False, feature_names_out=None)
