"""Tests for trails_compat — the Trails framework compatibility check."""
from __future__ import annotations

import pytest


def test_check_trails_against_live():
    """The live Trails install must satisfy the declared range."""
    try:
        from trails_compat import check_trails
    except ImportError as exc:
        pytest.skip(f"trails_compat not ready: {exc}")
    result = check_trails()
    assert result.satisfied, (
        f"declared Trails range {result.required!r} does not match "
        f"installed Trails {result.installed!r}: {result.note}"
    )


def test_satisfies_helper_handles_in_range():
    from trails_compat import _satisfies
    ok, _ = _satisfies("0.1.0a0", ">=0.1.0a0, <0.2.0")
    assert ok


def test_satisfies_helper_handles_out_of_range_high():
    from trails_compat import _satisfies
    ok, note = _satisfies("0.2.0", ">=0.1.0a0, <0.2.0")
    assert not ok, note


def test_satisfies_helper_handles_out_of_range_low():
    from trails_compat import _satisfies
    ok, note = _satisfies("0.0.9", ">=0.1.0a0, <0.2.0")
    assert not ok, note


def test_enforce_does_not_raise_in_dev(monkeypatch):
    """In dev (no TRAILS_ENV=production) a mismatch must log + continue."""
    from trails_compat import enforce, TrailsCompat
    monkeypatch.delenv("TRAILS_ENV", raising=False)
    monkeypatch.delenv("WD_ENV", raising=False)
    # Synthesise a mismatch report; enforce must not raise.
    mismatch = TrailsCompat(
        required=">=99.0.0",
        tested_against="99.0.0",
        installed="0.1.0a0",
        satisfied=False,
        note="synthesised mismatch",
    )
    enforce(mismatch)  # would raise on prod


def test_enforce_raises_in_production(monkeypatch):
    """When TRAILS_ENV=production, a mismatch must fail fast."""
    from trails_compat import enforce, TrailsCompat
    monkeypatch.setenv("TRAILS_ENV", "production")
    monkeypatch.delenv("WD_TRAILS_FAIL_OPEN", raising=False)
    mismatch = TrailsCompat(
        required=">=99.0.0",
        tested_against="99.0.0",
        installed="0.1.0a0",
        satisfied=False,
        note="synthesised mismatch",
    )
    with pytest.raises(RuntimeError):
        enforce(mismatch)


def test_enforce_fail_open_overrides_production(monkeypatch):
    """WD_TRAILS_FAIL_OPEN=1 must convert the production fail-fast to a warning."""
    from trails_compat import enforce, TrailsCompat
    monkeypatch.setenv("TRAILS_ENV", "production")
    monkeypatch.setenv("WD_TRAILS_FAIL_OPEN", "1")
    mismatch = TrailsCompat(
        required=">=99.0.0",
        tested_against="99.0.0",
        installed="0.1.0a0",
        satisfied=False,
        note="synthesised mismatch",
    )
    enforce(mismatch)  # must not raise


def test_version_endpoint_surfaces_trails_block():
    """/api/version must include the trails compat block."""
    try:
        from fastapi.testclient import TestClient
        from app import create_app
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    client = TestClient(create_app())
    doc = client.get("/api/version").json()
    assert "trails" in doc
    t = doc["trails"]
    assert {"required", "installed", "satisfied", "note"}.issubset(t)
    assert t["satisfied"] is True
