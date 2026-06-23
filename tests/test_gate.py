"""Tests for the quality gate (gate on pr_auc)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import gate  # noqa: E402


def _write_metrics(tmp_path: Path, pr_auc: float) -> Path:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"pr_auc": pr_auc, "f1": pr_auc}), encoding="utf-8")
    return p


def test_gate_blocks_worse_model(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path, 0.60)
    baseline_file = tmp_path / "baseline.txt"
    baseline_file.write_text("0.65\n", encoding="utf-8")
    code = gate.main(["--metrics", str(metrics), "--baseline-file", str(baseline_file)])
    assert code == 1
    assert baseline_file.read_text().strip() == "0.65"  # no promotion


def test_gate_passes_and_promotes_better_model(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path, 0.70)
    baseline_file = tmp_path / "baseline.txt"
    baseline_file.write_text("0.65\n", encoding="utf-8")
    code = gate.main(["--metrics", str(metrics), "--baseline-file", str(baseline_file)])
    assert code == 0
    assert float(baseline_file.read_text().strip()) == 0.70


def test_gate_blocks_equal_model(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path, 0.65)
    baseline_file = tmp_path / "baseline.txt"
    baseline_file.write_text("0.65\n", encoding="utf-8")
    code = gate.main(["--metrics", str(metrics), "--baseline-file", str(baseline_file)])
    assert code == 1  # an equal score is not enough


def test_gate_first_run_no_baseline(tmp_path: Path) -> None:
    metrics = _write_metrics(tmp_path, 0.5)
    baseline_file = tmp_path / "baseline.txt"  # does not exist
    code = gate.main(["--metrics", str(metrics), "--baseline-file", str(baseline_file)])
    assert code == 0
    assert baseline_file.exists()
