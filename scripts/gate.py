#!/usr/bin/env python3
"""Quality gate (metric gating) for churn — compares pr_auc vs baseline.

A model goes "to production" ONLY when its pr_auc is HIGHER than the current
baseline (the best result so far). This guards against quality regression:
a worse/equal model does NOT pass (exit 1) and blocks deployment.

For imbalanced classification the right metric is pr_auc (average
precision), not accuracy — so we gate on pr_auc.

Behavior:
  1. Reads ``metrics.json`` -> the ``pr_auc`` field.
  2. Reads the threshold from ``baseline.txt`` (or from ``--baseline``).
  3. pr_auc <= baseline -> exit 1 (CI stop, deployment blocked).
  4. pr_auc >  baseline -> exit 0; promotes (overwrites baseline.txt), unless
     ``--no-promote`` or a manual ``--baseline`` is given.

Usage:
    python scripts/gate.py [--metrics metrics.json] [--baseline-file baseline.txt]
                           [--baseline 0.65] [--no-promote]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_METRICS = Path("metrics.json")
DEFAULT_BASELINE_FILE = Path("baseline.txt")
METRIC_KEY = "pr_auc"


def read_metrics(path: Path) -> dict:
    if not path.exists():
        print(f"[GATE] ERROR: metrics file not found: {path} | metrics file not found")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def read_baseline(baseline_file: Path, override: float | None) -> float:
    if override is not None:
        return override
    if baseline_file.exists():
        raw = baseline_file.read_text(encoding="utf-8").strip()
        if raw:
            return float(raw)
    return 0.0  # no baseline = first run


def promote(baseline_file: Path, new_value: float) -> None:
    baseline_file.write_text(f"{new_value:.4f}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metric gate (pr_auc) for churn CI/CD")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--baseline-file", type=Path, default=DEFAULT_BASELINE_FILE)
    parser.add_argument(
        "--baseline",
        type=float,
        default=None,
        help="Override the baseline threshold (ignores baseline.txt) — for the demo.",
    )
    parser.add_argument("--no-promote", action="store_true")
    args = parser.parse_args(argv)

    metrics = read_metrics(args.metrics)
    pr_auc = float(metrics.get(METRIC_KEY, 0.0))
    baseline = read_baseline(args.baseline_file, args.baseline)

    print("[GATE] Quality gate (metric: pr_auc)")
    print(f"[GATE]   model pr_auc    : {pr_auc:.4f}")
    print(f"[GATE]   baseline thresh : {baseline:.4f}")

    if pr_auc <= baseline:
        print(
            f"[GATE] BLOCKED: pr_auc {pr_auc:.4f} <= baseline {baseline:.4f}. "
            "Model is not better — deployment halted."
        )
        print(f"[GATE] BLOCKED: pr_auc {pr_auc:.4f} <= baseline {baseline:.4f}.")
        return 1

    print(f"[GATE] OK: pr_auc {pr_auc:.4f} > baseline {baseline:.4f}. Deployment allowed.")

    if args.no_promote or args.baseline is not None:
        print("[GATE] Promotion skipped (demo mode / --no-promote).")
    else:
        promote(args.baseline_file, pr_auc)
        print(f"[GATE] Promoted. New baseline: {pr_auc:.4f} -> {args.baseline_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
