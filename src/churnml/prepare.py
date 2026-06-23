"""DVC pipeline `prepare` stage: data/raw.csv -> data/processed/{train,test}.csv.

Reads the split parameters from params.yaml (prepare.test_size, prepare.seed),
does a stratified split and writes two CSV files (train contains the label),
which become the input (deps) of the `train` stage.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sklearn.model_selection import train_test_split

from churnml.data import TARGET, load_raw

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "processed"


def main() -> None:
    params = yaml.safe_load((ROOT / "params.yaml").read_text())["prepare"]

    df = load_raw()
    y = (df[TARGET].astype(str).str.strip() == "Yes").astype(int)

    train_df, test_df = train_test_split(
        df,
        test_size=params["test_size"],
        random_state=params["seed"],
        stratify=y,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(OUT_DIR / "train.csv", index=False)
    test_df.to_csv(OUT_DIR / "test.csv", index=False)
    print(f"prepare: {len(train_df)} train / {len(test_df)} test -> {OUT_DIR}")


if __name__ == "__main__":
    main()
