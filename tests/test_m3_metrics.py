"""M3 — multi-group metrics tests.

Verify the three metrics produce sensible values on the curated
Querdenker fixture:
  - 2019 (pre-fracture): unanimous lateral sense -> entropy 0, low
    divergence, fragmentation > 0 only from group spread on a single
    sense (joint Gini-Simpson).
  - 2020 (fracture): groups split between lateral and covid ->
    entropy > 0, group divergence > 0, fragmentation high.
  - 2023 (consolidation): covid dominant; lateral survives only in
    querdenken-supporters -> entropy still > 0 because one group holds
    the minority sense; divergence still > 0.

Math is hand-derived where the assertion margins are tight; for
year-2019 lateral consensus the value is exactly 0 by construction.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ctx():
    from loader import load_all_ttl
    from trails.context import Context
    from trails.runtime import _kernel_store
    load_all_ttl(data_root=_REPO_ROOT)
    return Context(trace_id="test-m3", principal="system:test", store=_kernel_store())


def test_entropy_2019_is_zero_because_lateral_only():
    """All groups attest 'lateral' at 2019 — entropy must be exactly 0."""
    try:
        from capabilities.metrics_multi_group import semantic_entropy
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = semantic_entropy(ctx.kg, word="Querdenker", year=2019)
    # n_senses should be 1, so entropy is 0 by construction.
    assert result["n_senses"] == 1, f"expected 1 sense at 2019, got {result}"
    assert result["value"] == 0.0


def test_entropy_2020_is_strictly_positive():
    """2020 shows fragmentation -> entropy > 0."""
    try:
        from capabilities.metrics_multi_group import semantic_entropy
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = semantic_entropy(ctx.kg, word="Querdenker", year=2020)
    assert result["n_senses"] == 2, f"expected 2 senses at 2020, got {result}"
    assert result["value"] is not None and result["value"] > 0.0


def test_fragmentation_increases_2019_to_2020():
    """Fragmentation index must grow from pre-fracture to fracture year."""
    try:
        from capabilities.metrics_multi_group import semantic_fragmentation_index
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    f2019 = semantic_fragmentation_index(ctx.kg, word="Querdenker", year=2019)
    f2020 = semantic_fragmentation_index(ctx.kg, word="Querdenker", year=2020)
    assert f2020["value"] > f2019["value"], (
        f"expected fragmentation to grow 2019 -> 2020; got "
        f"f2019={f2019['value']}, f2020={f2020['value']}"
    )


def test_group_divergence_zero_at_2019_positive_at_2020():
    """Groups agree at 2019 -> JSD ~ 0; disagree at 2020 -> JSD > 0."""
    try:
        from capabilities.metrics_multi_group import group_divergence
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    d2019 = group_divergence(ctx.kg, word="Querdenker", year=2019)
    d2020 = group_divergence(ctx.kg, word="Querdenker", year=2020)

    # At 2019 all groups agree on lateral -> JSD = 0 exactly.
    assert d2019["max"] == 0.0, f"expected max JSD = 0 at 2019, got {d2019}"
    # At 2020 mainstream press flips to covid while querdenken supporters stay lateral.
    assert d2020["max"] is not None and d2020["max"] > 0.0, (
        f"expected max JSD > 0 at 2020, got {d2020}"
    )


def test_jsd_between_pure_opposed_distributions_is_one_bit():
    """JSD between two single-class distributions on different classes = 1."""
    try:
        from capabilities.metrics_multi_group import _jsd
    except ImportError as exc:
        pytest.skip(f"metrics module not ready: {exc}")
    j = _jsd({"a": 1.0}, {"b": 1.0})
    # Theoretical max JSD between two pure but disjoint distributions in bits is 1.
    assert abs(j - 1.0) < 1e-9, f"expected JSD = 1 bit, got {j}"


def test_metric_timeline_returns_one_row_per_year():
    """Timeline helper returns a non-empty per-year series."""
    try:
        from capabilities.metrics_multi_group import metric_timeline
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    tl = metric_timeline(ctx.kg, word="Querdenker")
    years = [row["year"] for row in tl]
    assert sorted(years) == years, "timeline should be year-ordered"
    assert len(years) >= 4, f"expected >=4 years in fixture, got {years}"


def test_low_evidence_returns_null_not_zero():
    """A word with no attributions returns None, not 0 — design contract."""
    try:
        from capabilities.metrics_multi_group import semantic_entropy
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = semantic_entropy(ctx.kg, word="NonExistentWord12345", year=2020)
    assert result["value"] is None
    assert result.get("reason") == "low_evidence"


def test_fragmentation_2020_matches_hand_calc():
    """Fragmentation at 2020 = 1 - sum_of_squares of joint (g,s) probabilities.

    Fixture (2020) — six (g,s) cells with weights:
      mp/covid 0.75, mp/lateral 0.25, lp/covid 0.7, qs/lateral 1.0,
      cc/lateral 0.7, al/lateral 0.5, al/covid 0.5
    -> 7 cells; total = 0.75+0.25+0.7+1.0+0.7+0.5+0.5 = 4.4
    -> sum_of_squares = sum( (w/4.4)^2 )
    """
    try:
        from capabilities.metrics_multi_group import semantic_fragmentation_index
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    result = semantic_fragmentation_index(ctx.kg, word="Querdenker", year=2020)
    weights = [0.75, 0.25, 0.7, 1.0, 0.7, 0.5, 0.5]
    total = sum(weights)
    expected = 1.0 - sum((w / total) ** 2 for w in weights)
    assert abs(result["value"] - expected) < 1e-6, (
        f"fragmentation mismatch: got {result['value']}, expected {expected}"
    )
    assert result["n_cells"] == 7
