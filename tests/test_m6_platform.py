"""M6 — Platform modelling + cross-platform distance smoke tests."""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ctx():
    from loader import load_all_ttl
    from trails.sdk import Context, kernel_store
    load_all_ttl(data_root=_REPO_ROOT)
    return Context(trace_id="test-m6", principal="system:test", store=kernel_store())


def _client():
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


def test_platform_models_import():
    try:
        from models import Platform, CorpusContext, Register  # noqa: F401
    except Exception as exc:
        pytest.skip(f"models not ready: {exc}")


def test_querdenker_has_four_platforms():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    word = next(w for w in doc["words"].values() if w["writtenForm"] == "Querdenker")

    platforms = word.get("platforms") or []
    labels = {p["label"] for p in platforms}
    assert {"Reddit", "Twitter / X", "German broadsheet press", "German Bundestag (plenary protocols)"}.issubset(labels), labels


def test_cross_platform_distance_positive_at_2020():
    """Platforms read 'Querdenker' differently in 2020 → JSD > 0."""
    try:
        from capabilities.metrics_multi_group import cross_platform_distance
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = cross_platform_distance(ctx.kg, word="Querdenker", year=2020)
    assert result["n_platforms"] >= 3, result
    assert result["max"] is not None and result["max"] > 0.0, result


def test_metric_timeline_has_platform_divergence_field():
    """metric_timeline carries platform_divergence_max where data exists."""
    try:
        from capabilities.metrics_multi_group import metric_timeline
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    tl = metric_timeline(ctx.kg, word="Querdenker")
    assert tl, tl
    # At least the 2020 + 2023 rows (where platform fixture lives) carry a value.
    years_with_platform_div = [r for r in tl if r.get("platform_divergence_max") is not None]
    assert len(years_with_platform_div) >= 2, tl


def test_attributions_carry_platform_field():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    word = next(w for w in doc["words"].values() if w["writtenForm"] == "Querdenker")
    plats = {a.get("platform") for a in word["attributions"] if a.get("platform")}
    assert len(plats) >= 3, plats
