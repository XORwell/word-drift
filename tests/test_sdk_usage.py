"""Smoke tests for the ``trails.sdk`` import surface (ADR-0082).

word-drift consumes Trails exclusively through ``trails.sdk`` per
ADR-0082 (commit 80bb9d0 on framework.trails). These tests are a thin
dogfood guard: if the SDK surface ever stops re-exporting one of the
symbols word-drift depends on, this file fails before the heavier M*
suites do, so the operator sees the boundary break, not the symptom.

Scope is intentionally minimal:

* the ``__sdk_version__`` string is non-empty (the SDK's own self-claim);
* an end-to-end smoke through the SDK proves we can build a ``Context``
  with ``kernel_store()``, run a COUNT(*) SELECT, and see > 0 triples
  after ``loader.load_all_ttl()``.

These tests skip (rather than fail) when Trails is not importable, in
the same style as the other tests/ modules in this repo.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_sdk_version_string_present():
    """``trails.sdk.__sdk_version__`` exists and is a non-empty string."""
    try:
        import trails.sdk as sdk
    except ImportError as exc:
        pytest.skip(f"trails.sdk not importable: {exc}")

    version = getattr(sdk, "__sdk_version__", None)
    assert isinstance(version, str), (
        f"__sdk_version__ should be a str, got {type(version).__name__}"
    )
    assert version, "__sdk_version__ should be non-empty"


def test_sdk_end_to_end_count_after_load():
    """Build a ``Context`` via the SDK surface and prove COUNT(*) > 0."""
    try:
        from trails.sdk import Context, kernel_store
        from loader import load_all_ttl
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)

    ctx = Context(
        trace_id="test-sdk-smoke",
        principal="system:test",
        store=kernel_store(),
    )
    rows = ctx.kg.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    assert rows, "COUNT(*) query should return at least one binding row"
    n = int(rows[0].get("n", 0))
    assert n > 0, f"expected > 0 triples after load_all_ttl, got {n}"
