"""Loading and splitting the churn data.

`load_data()` returns a stratified split (X_train, X_test, y_train, y_test)
from `data/raw.csv`. The `Churn` (Yes/No) label is encoded as 1/0. The
`customerID` column is an identifier (dropped from features).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw.csv"

TARGET = "Churn"
ID_COL = "customerID"
RANDOM_STATE = 42


def load_raw(path: Path | str = RAW) -> pd.DataFrame:
    """Load the raw churn CSV."""
    return pd.read_csv(path)


def split_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split the frame into features X and a binary label y (1 = churn)."""
    y = (df[TARGET].astype(str).str.strip() == "Yes").astype(int)
    X = df.drop(columns=[c for c in (TARGET, ID_COL) if c in df.columns])
    return X, y


def load_data(
    path: Path | str = RAW,
    test_size: float = 0.2,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Load the churn data and split it stratified into train/test.

    Returns:
        (X_train, X_test, y_train, y_test)
    """
    df = load_raw(path)
    X, y = split_xy(df)
    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
