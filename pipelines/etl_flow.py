"""Prefect ETL flow: extract -> validate -> features -> load (parquet).

Churn data pipeline orchestrated with Prefect (runs fully locally, no
server). Stages:

  1. extract   — read the raw CSV,
  2. validate  — check the Pandera contract (RAISES on dirty data),
  3. features  — feature engineering churnml.features.engineer,
  4. load      — write the processed data to Parquet (+ a CSV copy).

If `validate` detects an anomaly, the flow stops with a readable error,
and the `features`/`load` stages do NOT run — dirty data does not leak further.

Run:
    python pipelines/etl_flow.py data/raw.csv             # success
    python pipelines/etl_flow.py data/raw_corrupted.csv   # validation failure (exit 1)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from prefect import flow, get_run_logger, task

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

try:
    from pipelines.schema import churn_schema
except ImportError:
    sys.path.insert(0, str(ROOT))
    from pipelines.schema import churn_schema

from churnml.features import engineer  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"


@task
def extract(csv_path: str) -> pd.DataFrame:
    """Reads the raw churn CSV."""
    logger = get_run_logger()
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}. Run 'make data'.")
    df = pd.read_csv(path)
    logger.info("EXTRACT: read %d rows from %s", len(df), path)
    return df


@task
def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validates the frame against the Pandera contract (lazy -> all violations at once)."""
    logger = get_run_logger()
    try:
        validated = churn_schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failures = exc.failure_cases[["column", "check", "failure_case"]].head(20)
        logger.error(
            "VALIDATE: FAILED — %d contract violations:\n%s",
            len(exc.failure_cases),
            failures.to_string(index=False),
        )
        raise
    logger.info("VALIDATE: OK — %d rows satisfy the contract.", len(validated))
    return validated


@task
def features(df: pd.DataFrame) -> pd.DataFrame:
    """Churn feature engineering (derived features)."""
    logger = get_run_logger()
    out = engineer(df)
    new = ["tenure_bucket", "charges_per_tenure", "n_addons"]
    logger.info("FEATURES: added features: %s", ", ".join(new))
    return out


@task
def load(df: pd.DataFrame) -> Path:
    """Writes the processed data to Parquet (+ a CSV copy)."""
    logger = get_run_logger()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = PROCESSED_DIR / "churn_features.parquet"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(PROCESSED_DIR / "churn_features.csv", index=False)
    logger.info("LOAD: wrote %d rows -> %s", len(df), parquet_path)
    return parquet_path


@flow(name="churn-etl")
def churn_etl(csv_path: str = "data/raw.csv") -> Path:
    """Main flow: extract -> validate -> features -> load."""
    raw = extract(csv_path)
    clean = validate(raw)        # stops the flow on dirty data
    feats = features(clean)
    return load(feats)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "data/raw.csv"
    result = churn_etl(source)
    print(f"\nDone. Processed data -> {result}")
