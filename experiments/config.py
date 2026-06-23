"""Shared MLflow configuration for the churn experiment scripts.

A consistent backend for the UI and scripts: a local SQLite database
(`mlflow.db`) in the project directory (ABSOLUTE path) + artifacts in
`./mlartifacts`. Can be overridden with the `MLFLOW_TRACKING_URI` environment
variable.
"""

from __future__ import annotations

import os
from pathlib import Path

import mlflow

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TRACKING_URI = f"sqlite:///{ROOT / 'mlflow.db'}"

MODEL_NAME = "churn-clf"
EXPERIMENT_NAME = "churn"


def setup_mlflow() -> str:
    """Set the tracking URI and experiment. Returns the URI used."""
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)
    return tracking_uri
