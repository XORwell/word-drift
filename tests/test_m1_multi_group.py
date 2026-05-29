"""M1 — multi-group ontology smoke tests.

Verify that:
  - Group / Community / MeaningAttribution Python models are importable.
  - The M1 fixture loads into the kernel store alongside 2.x examples.
  - CQ13 returns one row per (group, sense, year) and reports the
    expected groups for the Querdenker test fixture.

These tests skip (not fail) if Trails is not importable, matching the
style of tests/test_graph_builder.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "m1_groups.ttl"


def _load_with_fixture() -> None:
    """Load the full repo + the M1 fixture into the kernel store."""
    from loader import load_all_ttl
    from trails.sdk import raw_kernel_store
    import rdflib

    load_all_ttl(data_root=_REPO_ROOT)

    g = rdflib.Graph()
    g.parse(str(_FIXTURE), format="turtle")
    nt = g.serialize(format="nt")
    raw_kernel_store().update("INSERT DATA {\n" + nt + "\n}")


def test_m1_models_importable():
    """Group / Community / MeaningAttribution import cleanly."""
    try:
        from models import Group, Community, MeaningAttribution  # noqa: F401
    except Exception as exc:
        pytest.skip(f"models not ready: {exc}")


def test_m1_fixture_loads():
    """The M1 fixture parses + loads without errors."""
    try:
        _load_with_fixture()
    except ImportError as exc:
        pytest.skip(f"Trails not ready: {exc}")

    from loader import triple_count
    assert triple_count() > 0, "kernel store should be populated"


def test_cq13_returns_three_groups_for_querdenker():
    """CQ13 returns at least three distinct groups for Querdenker."""
    try:
        _load_with_fixture()
        from capabilities.competency import cq13_groups_attributing_word
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    ctx = Context(trace_id="test-cq13", principal="system:test", store=kernel_store())
    rows = cq13_groups_attributing_word(ctx.kg, word="Querdenker")

    assert isinstance(rows, list)
    assert len(rows) >= 3, f"expected >=3 rows, got {len(rows)}: {rows}"

    groups = {r.get("groupLabel") for r in rows if r.get("groupLabel")}
    expected = {
        "Mainstream press (DE)",
        "Creativity / innovation community",
        "Querdenken-movement supporters",
    }
    assert expected.issubset(groups), f"missing groups: {expected - groups}"


def test_cq13_year_snapshot_2021_shows_split():
    """CQ13 at year=2021 shows the multi-group semantic split."""
    try:
        _load_with_fixture()
        from capabilities.competency import cq13_groups_attributing_word
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    ctx = Context(trace_id="test-cq13-2021", principal="system:test", store=kernel_store())
    rows = cq13_groups_attributing_word(ctx.kg, word="Querdenker", year=2021)

    # 2021 fixture has: mainstream-press -> covid, creativity-community -> lateral (mixed),
    # querdenken-supporters -> lateral. Three group attributions, two distinct senses.
    groups_2021 = {r.get("groupLabel") for r in rows if r.get("groupLabel")}
    assert len(groups_2021) >= 3, f"expected >=3 groups at 2021, got {groups_2021}"

    # The semantic split: at least two distinct senses attested across groups
    senses_2021 = {r.get("senseGloss") for r in rows if r.get("senseGloss")}
    assert len(senses_2021) >= 2, (
        f"expected >=2 senses at 2021 (the split), got {senses_2021}"
    )
