"""Promotes the best run (by pr_auc) and assigns its model version the @production alias.

Promotion policy (deterministic):
  1. maximum pr_auc,
  2. on a tie: simpler/faster model (lower 'complexity': logreg < hgb),
  3. then: fewer iterations (max_iter).

MLflow 3 uses **aliases** instead of "stages". The script:
  1. sets the ``production`` alias on the best version (the alias is unique —
     moving it removes it from the previous version),
  2. assigns a readable ``stage=Production`` tag and CLEARS it from previous versions,
  3. also attempts the classic stage (no-op on newer backends).
"""

from __future__ import annotations

import sys
from pathlib import Path

from mlflow.tracking import MlflowClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import EXPERIMENT_NAME, MODEL_NAME, setup_mlflow  # noqa: E402

PRODUCTION_ALIAS = "production"


def selection_key(run):
    """DESCENDING sort key: (pr_auc, -complexity, -max_iter)."""
    pr_auc = float(run.data.metrics.get("pr_auc", 0.0))
    complexity = int(float(run.data.params.get("complexity", 10**9)))
    max_iter = int(float(run.data.params.get("max_iter", 10**9)))
    return (pr_auc, -complexity, -max_iter)


def main() -> None:
    tracking_uri = setup_mlflow()
    print(f"MLFLOW_TRACKING_URI = {tracking_uri}")

    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise SystemExit(f"No experiment '{EXPERIMENT_NAME}'. Run: make train")

    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    # Take only runs with the pr_auc metric (skip the optuna-study parent run).
    runs = [r for r in runs if "pr_auc" in r.data.metrics]
    if not runs:
        raise SystemExit("No runs with pr_auc. Run: make train")

    runs_sorted = sorted(runs, key=selection_key, reverse=True)
    best_run = runs_sorted[0]
    best_run_id = best_run.info.run_id
    best_pr = best_run.data.metrics["pr_auc"]

    tied = [r for r in runs if float(r.data.metrics.get("pr_auc", 0.0)) == best_pr]
    print(f"Best run: {best_run_id} (pr_auc={best_pr:.4f})")
    if len(tied) > 1:
        print(
            f"  Tie: {len(tied)} runs with pr_auc={best_pr:.4f}. "
            f"Tiebreak -> simpler/faster: complexity="
            f"{best_run.data.params.get('complexity')}, "
            f"max_iter={best_run.data.params.get('max_iter')}."
        )

    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    matching = [v for v in versions if v.run_id == best_run_id]
    if not matching:
        raise SystemExit(f"No version of '{MODEL_NAME}' for run {best_run_id}.")
    best_version = max(matching, key=lambda v: int(v.version))
    print(f"Promoting {MODEL_NAME} v{best_version.version} -> @{PRODUCTION_ALIAS}")

    # 1) Alias 'production' (MLflow 3) — unique, moves automatically.
    client.set_registered_model_alias(
        name=MODEL_NAME, alias=PRODUCTION_ALIAS, version=best_version.version
    )

    # 2) Tag stage=Production — clear it from previous versions (the tag is not unique).
    for v in client.search_model_versions(f"name='{MODEL_NAME}'"):
        if v.version != best_version.version and v.tags.get("stage") == "Production":
            client.delete_model_version_tag(name=MODEL_NAME, version=v.version, key="stage")
    client.set_model_version_tag(
        name=MODEL_NAME, version=best_version.version, key="stage", value="Production"
    )

    # 3) Classic stage (local SQLite/file backend).
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=best_version.version,
                stage="Production",
                archive_existing_versions=True,
            )
    except Exception as exc:
        print(f"  (info) classic stage skipped: {exc}")

    print(
        f"Done. {MODEL_NAME} v{best_version.version} = @{PRODUCTION_ALIAS}. "
        f'Load with: mlflow.sklearn.load_model("models:/{MODEL_NAME}@{PRODUCTION_ALIAS}")'
    )


if __name__ == "__main__":
    main()
