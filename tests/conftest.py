"""Pytest setup — makes the test suite hermetic.

Ensures `data/raw.csv` exists by synthesizing it on first use, so the tests run on
a clean checkout (e.g. CI) without a prior `make data`. If real data already exists
it is left untouched. The generated file is git-ignored.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _ensure_raw_data() -> None:
    raw = ROOT / "data" / "raw.csv"
    if raw.exists():
        return
    from make_data import synthesize

    raw.parent.mkdir(parents=True, exist_ok=True)
    synthesize(n=3000, seed=42).to_csv(raw, index=False)


_ensure_raw_data()
