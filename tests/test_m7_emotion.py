"""M7 — emotional framing smoke tests."""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ctx():
    from loader import load_all_ttl
    from trails.context import Context
    from trails.runtime import _kernel_store
    load_all_ttl(data_root=_REPO_ROOT)
    return Context(trace_id="m7", principal="system:test", store=_kernel_store())


def _client():
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


def test_emotional_framing_model_imports():
    try:
        from models import EmotionalFraming  # noqa: F401
    except Exception as exc:
        pytest.skip(f"models not ready: {exc}")


def test_emotional_drift_returns_per_group_per_year():
    try:
        from capabilities.metrics_multi_group import emotional_drift
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = emotional_drift(ctx.kg, word="Querdenker")
    assert result["timeline"], result
    # At least 2 groups with framing data (mainstream press + querdenken-supporters).
    assert result["n_groups"] >= 2, result


def test_querdenken_supporters_valence_is_positive():
    """In-group framing of the lateral sense should be positive (admiring)."""
    try:
        from capabilities.metrics_multi_group import emotional_drift
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = emotional_drift(ctx.kg, word="Querdenker")
    qs_rows = [r for r in result["timeline"] if "Querdenken" in (r.get("groupLabel") or "")]
    assert qs_rows, result["timeline"]
    for r in qs_rows:
        assert r["valence_mean"] > 0, r


def test_mainstream_press_valence_is_negative():
    """Mainstream press framing of the covid sense is negative (hostile)."""
    try:
        from capabilities.metrics_multi_group import emotional_drift
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = emotional_drift(ctx.kg, word="Querdenker")
    mp_rows = [
        r for r in result["timeline"]
        if (r.get("groupLabel") or "").startswith("Mainstream press")
    ]
    assert mp_rows, result["timeline"]
    for r in mp_rows:
        assert r["valence_mean"] < 0, r


def test_endpoint_includes_emotional_drift():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    word = next(w for w in doc["words"].values() if w["writtenForm"] == "Querdenker")
    assert "emotional_drift" in word, word.keys()
    assert (word["emotional_drift"] or {}).get("timeline"), word["emotional_drift"]
