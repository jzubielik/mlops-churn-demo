"""Creates data/raw_corrupted.csv — deliberately dirty data for the validation demo.

Introduces realistic anomalies that break the Pandera contract (pipelines/schema.py):
* negative tenure (tenure = -5)          -> out of range,
* absurd MonthlyCharges (9999.0)         -> out of range,
* unknown Contract category              -> outside the allowed set,
* text in the numeric TotalCharges column -> wrong type after reading from CSV.

Built on freshly synthesized clean data (deterministically).
"""

from __future__ import annotations

from pathlib import Path

from make_data import synthesize  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw_corrupted.csv"


def main() -> None:
    df = synthesize(n=200, seed=42).copy()

    df.loc[0, "tenure"] = -5
    df.loc[1, "MonthlyCharges"] = 9999.0
    df.loc[2, "Contract"] = "Lifetime"

    df["TotalCharges"] = df["TotalCharges"].astype(object)
    df.loc[3, "TotalCharges"] = "not-a-number"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} rows with anomalies -> {OUT}")
    print(
        "Anomalies: tenure=-5, MonthlyCharges=9999, "
        "Contract='Lifetime', TotalCharges='not-a-number'."
    )


if __name__ == "__main__":
    main()
