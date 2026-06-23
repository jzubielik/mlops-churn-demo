"""Scaffold smoke test — the package imports and has a version.

Keeps `make test` green from the very first milestone; the actual logic
tests are added together with the code (m03+).
"""

import churnml


def test_package_imports():
    assert churnml.__version__ == "0.1.0"
