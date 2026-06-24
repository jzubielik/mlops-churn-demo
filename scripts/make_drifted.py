"""Generates cohorts to demonstrate churn data drift (Evidently 0.4.x).

Creates two CSV files in ``data/`` (without the target feature in drift analysis):

  data/reference.csv  — the "training" distribution (a sample from data/raw.csv),
  data/current.csv    — a simulated "future" cohort with injected drift.

Drift is injected RELIABLY: we shift the distributions of numeric features
(tenure down, MonthlyCharges up) AND over-weight the risky categories
(more Month-to-month, more Fiber optic, more Electronic check). This way
Evidently's DataDriftPreset stably reports dataset_drift=True.

Run:
    python scripts/make_drifted.py [--rows 2000] [--seed 7]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw.csv"
REFERENCE_CSV = ROOT / "data" / "reference.csv"
CURRENT_CSV = ROOT / "data" / "current.csv"

# Target column — skipped when analyzing drift of input features.
TARGET = "Churn"
ID_COL = "customerID"


def _load_reference(rows: int, seed: int) -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(
            f"[make-drifted] Missing {RAW}. Run first: make data (python scripts/make_data.py)."
        )
    df = pd.read_csv(RAW)
    if len(df) > rows:
        df = df.sample(n=rows, random_state=seed).reset_index(drop=True)
    return df.drop(columns=[c for c in (ID_COL,) if c in df.columns])


def make_drifted(reference: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    """Creates a cohort with clear, unambiguously detectable drift."""
    rng = np.random.default_rng(seed)
    drifted = reference.copy()
    n = len(drifted)

    # --- Drift of numeric features (shift + noise) -------------------------
    # "Future" customers: shorter tenure, higher monthly charges.
    drifted["tenure"] = np.clip(
        pd.to_numeric(drifted["tenure"]) * 0.45 + rng.normal(0, 2, n), 0, 72
    ).round().astype(int)
    drifted["MonthlyCharges"] = np.clip(
        pd.to_numeric(drifted["MonthlyCharges"]) + 22.0 + rng.normal(0, 4, n), 18.25, 130.0
    ).round(2)
    drifted["TotalCharges"] = np.clip(
        pd.to_numeric(drifted["TotalCharges"], errors="coerce").fillna(0.0) * 0.5
        + rng.normal(0, 30, n),
        18.25,
        None,
    ).round(2)

    # --- Drift of categorical features (over-weighting risky classes) ------
    drifted["Contract"] = rng.choice(
        ["Month-to-month", "One year", "Two year"], size=n, p=[0.85, 0.10, 0.05]
    )
    drifted["InternetService"] = rng.choice(
        ["DSL", "Fiber optic", "No"], size=n, p=[0.18, 0.74, 0.08]
    )
    drifted["PaymentMethod"] = rng.choice(
        [
            "Electronic check",
            "Mailed check",
            "Bank transfer (automatic)",
            "Credit card (automatic)",
        ],
        size=n,
        p=[0.70, 0.12, 0.10, 0.08],
    )
    drifted["PaperlessBilling"] = rng.choice(["Yes", "No"], size=n, p=[0.85, 0.15])

    # Add-on services: in the "future" cohort customers massively drop add-ons
    # (we over-weight "No") — this shifts these category distributions and grows drift.
    addon_cols = [
        "OnlineSecurity",
        "OnlineBackup",
        "DeviceProtection",
        "TechSupport",
        "StreamingTV",
        "StreamingMovies",
    ]
    for col in addon_cols:
        if col in drifted.columns:
            drifted[col] = rng.choice(["Yes", "No"], size=n, p=[0.08, 0.92])

    # Demographics: over-weight seniors and customers without a partner/dependents.
    if "SeniorCitizen" in drifted.columns:
        drifted["SeniorCitizen"] = rng.binomial(1, 0.55, n)
    if "Partner" in drifted.columns:
        drifted["Partner"] = rng.choice(["Yes", "No"], size=n, p=[0.20, 0.80])
    if "Dependents" in drifted.columns:
        drifted["Dependents"] = rng.choice(["Yes", "No"], size=n, p=[0.10, 0.90])

    return drifted


def main() -> None:
    parser = argparse.ArgumentParser(description="Generates the reference and drifted cohorts.")
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    reference = _load_reference(args.rows, args.seed)
    drifted = make_drifted(reference, seed=args.seed)

    reference.to_csv(REFERENCE_CSV, index=False)
    drifted.to_csv(CURRENT_CSV, index=False)

    print(f"[make-drifted] reference -> {REFERENCE_CSV} ({len(reference)} rows)")
    print(f"[make-drifted] drift     -> {CURRENT_CSV} ({len(drifted)} rows)")
    print(
        "[make-drifted] shifted features: tenure(-), MonthlyCharges(+), TotalCharges(-), "
        "Contract/InternetService/PaymentMethod/PaperlessBilling (over-weighted)."
    )


if __name__ == "__main__":
    main()
