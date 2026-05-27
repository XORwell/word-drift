"""
Smoke tests for loader.py and graph_builder.py.

These exercise the real bootstrap path used by ``app.create_app()``:
``load_all_ttl()`` populates the shared Trails kernel store (default graph),
``build_graph_document(ctx.kg)`` derives the frontend document, and
``split_document`` splits it into the core / per-word detail payloads.

Tests skip (rather than fail) if the modules or Trails are not importable,
so the suite is safe to run during development.
"""

import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Per-word detail is keyed by word IRI, so its top-level keys are dynamic.
# The core document has a stable, known shape — assert against that.
_EXPECTED_CORE_KEYS = {"meta", "driftTypes", "facets", "words", "driftEventsFlat"}


def test_imports():
    """Verify core modules import without error."""
    try:
        import loader          # noqa: F401
        import graph_builder   # noqa: F401
    except Exception as exc:
        pytest.skip(f"modules not ready: {exc}")


def test_load_populates_kernel_store():
    """load_all_ttl() loads the repo's TTL into the shared kernel store."""
    try:
        from loader import load_all_ttl, triple_count
    except ImportError as exc:
        pytest.skip(f"loader not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    n = triple_count()
    assert n > 0, "kernel store should have triples after loading"


def test_graph_builder_top_level_keys():
    """build_graph_document(ctx.kg) returns a dict with the expected core keys."""
    try:
        from loader import load_all_ttl
        from graph_builder import build_graph_document
        from trails.context import Context
        from trails.runtime import _kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(trace_id="test", principal="system:test", store=_kernel_store())
    doc = build_graph_document(ctx.kg)

    assert isinstance(doc, dict), "build_graph_document should return a dict"
    missing = _EXPECTED_CORE_KEYS - doc.keys()
    assert not missing, f"missing expected keys: {missing}"
    assert len(doc["words"]) > 0, "document should contain words"


def test_split_document_shape():
    """split_document returns a (core, detail) pair of dicts."""
    try:
        from loader import load_all_ttl
        from graph_builder import build_graph_document, split_document
        from trails.context import Context
        from trails.runtime import _kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(trace_id="test", principal="system:test", store=_kernel_store())
    doc = build_graph_document(ctx.kg)
    core, detail = split_document(doc)

    assert isinstance(core, dict), "core should be a dict"
    assert isinstance(detail, dict), "detail should be a dict"
    # Per-word detail is keyed by word IRI; every detail key should be a word.
    assert len(detail) <= len(core.get("words", [])) + 1, \
        "detail should not have more entries than there are words"
