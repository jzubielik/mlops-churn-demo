"""Churn data drift detection using Evidently (API 0.4.x).

Compares ``data/reference.csv`` (the "training" distribution) with ``data/current.csv``
(a simulated "future" cohort). Generates an HTML report, prints the drift result,
best-effort sends the drift share to the FastAPI service (POST /drift-score → gauge
``last_drift_score`` in Grafana) and — if drift exceeds the threshold — triggers
model retraining (data regeneration + training + quality gate).

Code written for Evidently 0.4.40 (Report + DataDriftPreset).

Environment variables:
    DRIFT_SHARE_THRESHOLD  threshold for the share of drifted columns (default 0.5)
    SERVICE_URL            address of the prediction service (default :17100)
    DRIFT_NO_RETRAIN       if set (=1), do not trigger retraining

Run:
    python monitoring/drift_check.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

# Evidently 0.4.x API.
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

PROJECT_DIR = Path(__file__).resolve().parent.parent
REFERENCE_CSV = PROJECT_DIR / "data" / "reference.csv"
CURRENT_CSV = PROJECT_DIR / "data" / "current.csv"
REPORT_HTML = PROJECT_DIR / "drift_report.html"

TARGET = "Churn"
ID_COL = "customerID"

DRIFT_SHARE_THRESHOLD = float(os.environ.get("DRIFT_SHARE_THRESHOLD", "0.5"))
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:17100")


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(
            f"[drift] File {path} is missing. Run first: make gen-drift "
            "(python scripts/make_drifted.py)."
        )
    df = pd.read_csv(path)
    # We skip the target + identifier in the input-feature drift analysis.
    return df.drop(columns=[c for c in (TARGET, ID_COL) if c in df.columns])


def run_drift_report() -> dict:
    """Run the Evidently report and return a dict summarizing the drift."""
    reference = _load(REFERENCE_CSV)
    current = _load(CURRENT_CSV)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)
    report.save_html(str(REPORT_HTML))

    result = report.as_dict()["metrics"][0]["result"]
    return {
        "dataset_drift": bool(result["dataset_drift"]),
        "drift_share": float(result["share_of_drifted_columns"]),
        "n_drifted": int(result["number_of_drifted_columns"]),
        "n_columns": int(result["number_of_columns"]),
    }


def push_drift_score(score: float) -> None:
    """Best-effort: send the drift share to the service (gauge in Grafana)."""
    url = f"{SERVICE_URL}/drift-score"
    data = json.dumps({"score": round(score, 4)}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            resp.read()
        print(f"[drift] Sent drift_score={score:.4f} -> {url}")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[drift] (info) Service unavailable at {url} — skipping push ({exc}).")


def trigger_retraining(summary: dict) -> None:
    """Retraining after drift is detected: data regeneration + training + gate."""
    ts = dt.datetime.now().isoformat(timespec="seconds")
    print("=" * 70)
    print(f"[retrain] {ts} DRIFT DETECTED — triggering retraining.")
    print(
        f"[retrain] Drifted columns: {summary['n_drifted']}/{summary['n_columns']} "
        f"(share={summary['drift_share']:.2f}, threshold={DRIFT_SHARE_THRESHOLD:.2f})"
    )
    print("=" * 70)

    if os.environ.get("DRIFT_NO_RETRAIN"):
        print("[retrain] DRIFT_NO_RETRAIN set — skipping the actual retraining.")
        return

    # Retraining via existing Makefile targets (data->prepare->train + gate).
    cmds = [
        ["make", "train-model"],
        ["make", "gate"],
    ]
    for cmd in cmds:
        print(f"[retrain] $ {' '.join(cmd)}")
        rc = subprocess.run(cmd, cwd=PROJECT_DIR).returncode
        if rc != 0:
            print(f"[retrain] WARNING: step {' '.join(cmd)} returned code {rc}.")
            return
    print("[retrain] Retraining finished — new model.joblib + metrics.json saved.")


def main() -> int:
    summary = run_drift_report()

    print("-" * 70)
    print(f"[drift] dataset_drift     : {summary['dataset_drift']}")
    print(f"[drift] drifted columns   : {summary['n_drifted']}/{summary['n_columns']}")
    print(f"[drift] drift share       : {summary['drift_share']:.2f}")
    print(f"[drift] HTML report       : {REPORT_HTML}")
    print("-" * 70)

    push_drift_score(summary["drift_share"])

    drift_detected = (
        summary["dataset_drift"] and summary["drift_share"] >= DRIFT_SHARE_THRESHOLD
    )
    if drift_detected:
        trigger_retraining(summary)
    else:
        print("[drift] No significant drift — retraining not needed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
