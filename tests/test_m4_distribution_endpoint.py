"""M4 — /graph-distribution.json endpoint smoke test.

Validates the new endpoint's shape against the curated Querdenker fixture.
The frontend (assets/views/distribution.js) consumes this directly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _client():
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


def test_graph_distribution_responds_200_and_has_querdenker():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    r = client.get("/graph-distribution.json")
    assert r.status_code == 200, r.text
    doc = r.json()

    assert "words" in doc
    words = doc["words"]
    assert any(w["writtenForm"] == "Querdenker" for w in words.values()), list(words)


def test_querdenker_record_has_expected_shape():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    doc = client.get("/graph-distribution.json").json()
    qkey = [k for k, w in doc["words"].items() if w["writtenForm"] == "Querdenker"][0]
    word = doc["words"][qkey]

    assert len(word["senses"]) == 2, f"expected 2 senses, got {len(word['senses'])}"
    # >=5 because the M1 fixture adds another 3 groups when both test files run
    # in the same pytest session (state-shared kernel store).
    assert len(word["groups"]) >= 5, f"expected >=5 groups, got {len(word['groups'])}"

    # No IRI duplication: each group IRI appears at most once.
    # (Two different IRIs may carry the same display label, e.g. when the
    # test fixture and the curated dataset share a label string. That is
    # legitimate; what must not happen is the same IRI being emitted twice
    # because of multilingual rdfs:label rows.)
    iris = [g["id"] for g in word["groups"]]
    assert len(iris) == len(set(iris)), f"duplicate group IRIs: {iris}"

    # Each attribution has the required fields and a real weight.
    for a in word["attributions"]:
        assert {"sense", "group", "year", "weight"}.issubset(a), a
        assert isinstance(a["weight"], (int, float))
        assert isinstance(a["year"], int)

    # Metric timeline has one entry per attested year.
    years = sorted({a["year"] for a in word["attributions"]})
    metric_years = [m["year"] for m in word["metrics"]]
    assert metric_years == years, (metric_years, years)


def test_existing_graph_core_still_works():
    """Backwards-compat: 2.x /graph-core.json must not regress."""
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    r = client.get("/graph-core.json")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert "words" in doc
    assert len(doc["words"]) > 0
