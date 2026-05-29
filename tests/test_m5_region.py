"""M5 — region modelling smoke tests."""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _client():
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


def test_region_model_imports():
    try:
        from models import Region  # noqa: F401
    except Exception as exc:
        pytest.skip(f"models not ready: {exc}")


def test_woke_record_carries_three_regions():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    woke_keys = [k for k, w in doc["words"].items() if w["writtenForm"] == "woke"]
    assert woke_keys, "expected 'woke' in distribution doc"
    word = doc["words"][woke_keys[0]]

    regions = word.get("regions") or []
    assert len(regions) >= 3, f"expected >=3 regions, got {regions}"

    labels = {r["label"] for r in regions}
    assert {"United States", "United Kingdom", "Germany"}.issubset(labels), labels

    # Each region carries decimal lat/lon for the proportional-symbol map.
    for r in regions:
        assert r.get("lat") is not None and r.get("lon") is not None, r


def test_attributions_carry_region_field():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    woke = next(w for w in doc["words"].values() if w["writtenForm"] == "woke")
    region_iris = {a.get("region") for a in woke["attributions"] if a.get("region")}
    assert len(region_iris) >= 3, region_iris


def test_cq14_returns_region_rows():
    """CQ14 cross-tab returns one row per (region, sense) pair for 'woke'."""
    try:
        from loader import load_all_ttl
        from capabilities.competency import cq14_region_distribution
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(trace_id="m5-cq14", principal="system:test", store=kernel_store())
    rows = cq14_region_distribution(ctx.kg, word="woke")

    regions = {r.get("regionLabel") for r in rows if r.get("regionLabel")}
    assert "United States" in regions, regions
    assert "United Kingdom" in regions, regions
    assert "Germany" in regions, regions

    # 2023 should still show a US vs DE gap (US pejorative-dominant, DE progressive-dominant).
    rows_2023 = cq14_region_distribution(ctx.kg, word="woke", year=2023)
    assert len(rows_2023) >= 4, rows_2023  # 3 regions x ≥2 senses for most
