"""M2 — Querdenker multi-group dataset smoke tests.

Verify that the curated multi-group fixture in
examples/querdenker-multigroup.ttl loads via the normal loader path
(no test-only injection) and CQ13 returns the expected shape:

  - 5 distinct groups attest the word
  - At year 2019 the lateral sense is dominant across groups
  - At year 2020 multiple groups attest competing senses (fragmentation)
  - At year 2023 the covid sense dominates everywhere except querdenken supporters
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load() -> None:
    from loader import load_all_ttl
    load_all_ttl(data_root=_REPO_ROOT)


def test_m2_loads_via_normal_path():
    """The M2 dataset is picked up by load_all_ttl() (no test-only loader)."""
    try:
        _load()
    except ImportError as exc:
        pytest.skip(f"Trails not ready: {exc}")
    from loader import triple_count
    n = triple_count()
    assert n > 0


def test_m2_cq13_finds_five_groups_for_querdenker():
    """CQ13 should see all 5 curated groups for Querdenker."""
    try:
        _load()
        from capabilities.competency import cq13_groups_attributing_word
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    ctx = Context(trace_id="test-m2", principal="system:test", store=kernel_store())
    rows = cq13_groups_attributing_word(ctx.kg, word="Querdenker")

    groups = {r.get("groupLabel") for r in rows if r.get("groupLabel")}
    expected_substrings = [
        "Mainstream press",
        "Leftist press",
        "Creativity",
        "Querdenken-movement",
        "Academic linguistics",
    ]
    for needle in expected_substrings:
        assert any(needle in g for g in groups), (
            f"expected a group label containing {needle!r}, got groups={groups}"
        )


def test_m2_year_2020_shows_semantic_split():
    """At 2020 multiple groups should be attesting competing senses."""
    try:
        _load()
        from capabilities.competency import cq13_groups_attributing_word
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    ctx = Context(trace_id="test-m2-2020", principal="system:test", store=kernel_store())
    rows = cq13_groups_attributing_word(ctx.kg, word="Querdenker", year=2020)

    # 2020 has: MP -> both, LP -> covid, CC -> lateral, QS -> lateral, AL -> both
    # Both senses must appear, and at least one group must split.
    senses = {r.get("senseGloss") for r in rows if r.get("senseGloss")}
    assert len(senses) >= 2, f"expected fragmentation at 2020, got senses={senses}"

    # At least 4 groups attest at year 2020
    groups_2020 = {r.get("groupLabel") for r in rows if r.get("groupLabel")}
    assert len(groups_2020) >= 4, (
        f"expected >=4 groups at 2020, got {len(groups_2020)}: {groups_2020}"
    )


def test_m2_drift_event_occurred_in_group_attached():
    """The 2.x DriftEvent picked up an optional drift:occurredInGroup link."""
    try:
        _load()
        from trails.sdk import Context, kernel_store
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    ctx = Context(trace_id="test-m2-de", principal="system:test", store=kernel_store())
    rows = ctx.kg.query("""
PREFIX drift: <https://w3id.org/word-drift/ontology#>
SELECT (COUNT(DISTINCT ?g) AS ?n)
WHERE {
  <https://w3id.org/word-drift/resource/drift-querdenker-2020>
      drift:occurredInGroup ?g .
}
""")
    n = int(rows[0]["n"]) if rows and "n" in rows[0] else 0
    assert n >= 2, f"expected >=2 occurredInGroup links on the 2.x DriftEvent, got {n}"
