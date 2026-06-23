"""Tests for churn feature engineering."""

import pandas as pd

from churnml.data import load_raw, split_xy
from churnml.features import ENGINEERED_NUMERIC, engineer


def _sample() -> pd.DataFrame:
    df = load_raw()
    X, _ = split_xy(df)
    return X.head(50)


def test_engineer_adds_expected_columns() -> None:
    X = _sample()
    out = engineer(X)
    for col in (*ENGINEERED_NUMERIC, "tenure_bucket"):
        assert col in out.columns


def test_engineer_preserves_row_count() -> None:
    X = _sample()
    out = engineer(X)
    assert len(out) == len(X)


def test_charges_per_tenure_nonnegative_and_finite() -> None:
    out = engineer(_sample())
    s = out["charges_per_tenure"]
    assert (s >= 0).all()
    assert s.notna().all()


def test_n_addons_in_range() -> None:
    out = engineer(_sample())
    # 7 possible add-on services -> values in [0, 7].
    assert out["n_addons"].between(0, 7).all()
