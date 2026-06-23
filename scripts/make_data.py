"""Deterministically synthesizes the Telco Customer Churn dataset -> data/raw.csv.

We do NOT download any data from the network — we generate a realistic, slightly
imbalanced (~26% churn) dataset with sensible business correlations:
month-to-month contract + low tenure + high MonthlyCharges -> higher
chance of leaving. The whole thing is repeatable (numpy seed), so `dvc repro` is
reproducible.

Columns (project contract):
    customerID, gender, SeniorCitizen, Partner, Dependents, tenure,
    PhoneService, MultipleLines, InternetService, OnlineSecurity, OnlineBackup,
    DeviceProtection, TechSupport, StreamingTV, StreamingMovies, Contract,
    PaperlessBilling, PaymentMethod, MonthlyCharges, TotalCharges, Churn(Yes/No)

Run:
    python scripts/make_data.py [--rows 7032] [--seed 42]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw.csv"

CONTRACTS = ["Month-to-month", "One year", "Two year"]
INTERNET = ["DSL", "Fiber optic", "No"]
PAYMENTS = [
    "Electronic check",
    "Mailed check",
    "Bank transfer (automatic)",
    "Credit card (automatic)",
]


def _pick(rng: np.random.Generator, options: list[str], probs, n: int) -> np.ndarray:
    return rng.choice(options, size=n, p=probs)


def synthesize(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    gender = _pick(rng, ["Female", "Male"], [0.5, 0.5], n)
    senior = rng.binomial(1, 0.16, n)
    partner = _pick(rng, ["Yes", "No"], [0.48, 0.52], n)
    dependents = _pick(rng, ["Yes", "No"], [0.30, 0.70], n)

    # tenure: a mix of new and loyal customers (0..72 months).
    tenure = np.clip(rng.gamma(shape=2.0, scale=14.0, size=n), 0, 72).round().astype(int)

    contract = _pick(rng, CONTRACTS, [0.55, 0.21, 0.24], n)
    internet = _pick(rng, INTERNET, [0.34, 0.44, 0.22], n)

    phone = _pick(rng, ["Yes", "No"], [0.90, 0.10], n)

    def dep_on_phone(yes_p: float) -> np.ndarray:
        out = np.where(
            phone == "No",
            "No phone service",
            _pick(rng, ["Yes", "No"], [yes_p, 1 - yes_p], n),
        )
        return out

    multiple_lines = dep_on_phone(0.42)

    def dep_on_internet(yes_p: float) -> np.ndarray:
        out = np.where(
            internet == "No",
            "No internet service",
            _pick(rng, ["Yes", "No"], [yes_p, 1 - yes_p], n),
        )
        return out

    online_security = dep_on_internet(0.35)
    online_backup = dep_on_internet(0.40)
    device_protection = dep_on_internet(0.40)
    tech_support = dep_on_internet(0.35)
    streaming_tv = dep_on_internet(0.49)
    streaming_movies = dep_on_internet(0.49)

    paperless = _pick(rng, ["Yes", "No"], [0.59, 0.41], n)
    payment = _pick(rng, PAYMENTS, [0.34, 0.23, 0.22, 0.21], n)

    # MonthlyCharges: based primarily on internet services + add-ons.
    base = np.where(internet == "Fiber optic", 70.0, np.where(internet == "DSL", 45.0, 20.0))
    addons = (
        (streaming_tv == "Yes").astype(float) * 6
        + (streaming_movies == "Yes").astype(float) * 6
        + (online_security == "Yes").astype(float) * 5
        + (online_backup == "Yes").astype(float) * 5
        + (device_protection == "Yes").astype(float) * 5
        + (tech_support == "Yes").astype(float) * 5
        + (multiple_lines == "Yes").astype(float) * 5
    )
    monthly = np.clip(base + addons + rng.normal(0, 3, n), 18.25, 120.0).round(2)

    # TotalCharges ~ monthly * tenure (with slight noise); a new customer ~ monthly.
    total = np.clip(monthly * np.maximum(tenure, 1) * rng.normal(1.0, 0.03, n), 18.25, None)
    total = np.where(tenure == 0, monthly, total).round(2)

    # --- Churn probability: logit with business correlations ---------------
    logit = (
        -2.15
        + (contract == "Month-to-month").astype(float) * 1.6
        + (contract == "Two year").astype(float) * (-1.4)
        + (contract == "One year").astype(float) * (-0.6)
        - 0.035 * tenure
        + 0.018 * (monthly - 65.0)
        + (internet == "Fiber optic").astype(float) * 0.7
        + (payment == "Electronic check").astype(float) * 0.5
        + (paperless == "Yes").astype(float) * 0.3
        + (tech_support == "No").astype(float) * 0.3
        + (online_security == "No").astype(float) * 0.3
        + senior * 0.25
        + (dependents == "No").astype(float) * 0.15
        + rng.normal(0, 0.35, n)
    )
    prob = 1.0 / (1.0 + np.exp(-logit))
    churn = np.where(rng.random(n) < prob, "Yes", "No")

    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    customer_id = [
        f"{rng.integers(1000, 9999)}-{''.join(rng.choice(letters, 5))}"
        for _ in range(n)
    ]

    df = pd.DataFrame(
        {
            "customerID": customer_id,
            "gender": gender,
            "SeniorCitizen": senior,
            "Partner": partner,
            "Dependents": dependents,
            "tenure": tenure,
            "PhoneService": phone,
            "MultipleLines": multiple_lines,
            "InternetService": internet,
            "OnlineSecurity": online_security,
            "OnlineBackup": online_backup,
            "DeviceProtection": device_protection,
            "TechSupport": tech_support,
            "StreamingTV": streaming_tv,
            "StreamingMovies": streaming_movies,
            "Contract": contract,
            "PaperlessBilling": paperless,
            "PaymentMethod": payment,
            "MonthlyCharges": monthly,
            "TotalCharges": total,
            "Churn": churn,
        }
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize the Telco churn dataset.")
    parser.add_argument("--rows", type=int, default=7032)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=RAW)
    args = parser.parse_args()

    df = synthesize(args.rows, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    rate = (df["Churn"] == "Yes").mean()
    print(f"Saved {len(df)} rows -> {args.out}")
    print(f"Churn positive rate: {rate:.3f}")


if __name__ == "__main__":
    main()
