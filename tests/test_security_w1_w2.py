"""Security regression tests for W1 (SPARQL injection) and W2 (/api/sparql)."""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ctx():
    from loader import load_all_ttl
    from trails.sdk import Context, kernel_store
    load_all_ttl(data_root=_REPO_ROOT)
    return Context(trace_id="test-sec", principal="system:test", store=kernel_store())


def _client():
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


# --- W1: parameter binding neutralises ?word= injection ---------------------

@pytest.mark.parametrize("payload", [
    'x"',
    'x"} UNION { ?s ?p ?o }',
    'Querdenker"} ; INSERT DATA { <urn:x> <urn:p> <urn:o> }',
    '" || true # ',
    "Querdenker' OR '1'='1",
])
def test_cq13_neutralises_injection_payload(payload):
    """Hostile payloads must never return the whole store via UNION/comment injection."""
    try:
        from capabilities.competency import cq13_groups_attributing_word
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    # Must not crash; must return an empty (or matching-only) result, not the
    # whole store. None of these payloads match a real Word.writtenForm, so
    # the result must be empty. If it isn't, the binding leaked.
    rows = cq13_groups_attributing_word(ctx.kg, word=payload)
    assert isinstance(rows, list)
    assert len(rows) == 0, f"injection payload {payload!r} returned {len(rows)} rows"


def test_control_char_payload_does_not_leak_unbounded_data():
    """A null-byte-suffixed real word may match if Oxigraph normalises STR(),
    but it must never return MORE rows than the legitimate word alone."""
    try:
        from capabilities.competency import cq13_groups_attributing_word
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")
    legit = cq13_groups_attributing_word(ctx.kg, word="Querdenker")
    nul   = cq13_groups_attributing_word(ctx.kg, word="Querdenker\x00")
    # Either equal (engine strips trailing null) or zero. Never more.
    assert len(nul) <= len(legit)


def test_attribution_rows_neutralises_quote():
    try:
        from capabilities.metrics_multi_group import _attribution_rows
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")
    rows = _attribution_rows(ctx.kg, word='x"')
    assert rows == []


def test_cq14_neutralises_injection():
    try:
        from capabilities.competency import cq14_region_distribution
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")
    rows = cq14_region_distribution(ctx.kg, word='x"} UNION { ?s ?p ?o }')
    assert rows == []


def test_legit_word_still_returns_data():
    """The parameterisation must not break legitimate queries."""
    try:
        from capabilities.competency import cq13_groups_attributing_word
        ctx = _ctx()
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")
    rows = cq13_groups_attributing_word(ctx.kg, word="Querdenker")
    assert len(rows) > 0
    # F1 fix: LANG filter eliminates label duplication. After W12 the
    # Wikipedia-revisions ingest contributes 4 additional editor-cohort
    # Groups (early-wiki / growth-wiki / late-wiki / post-2020 / anon)
    # to Querdenker on top of the 5 curated Groups (mainstream press,
    # leftist press, creativity community, Querdenken supporters,
    # academic linguistics) — so the upper bound is 10 (5 curated + 5
    # cohorts).
    labels = {r.get("groupLabel") for r in rows if r.get("groupLabel")}
    assert len(labels) <= 10, f"expected <=10 distinct labels, got {labels}"


# --- W2: /api/sparql allow-list ---------------------------------------------

def test_sparql_endpoint_allows_select():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/sparql", params={"query": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"})
    assert r.status_code == 200, r.text


def test_sparql_endpoint_allows_ask():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/sparql", params={"query": "ASK { ?s ?p ?o }"})
    assert r.status_code == 200


@pytest.mark.parametrize("payload", [
    "INSERT DATA { <urn:x> <urn:p> <urn:o> }",
    "DELETE WHERE { ?s ?p ?o }",
    "LOAD <http://example/data>",
    "CLEAR ALL",
    "DROP GRAPH <urn:default>",
    "CREATE GRAPH <urn:new>",
    # Sneaky: PREFIX then INSERT
    "PREFIX ex: <urn:ex#> INSERT DATA { ex:a ex:b ex:c }",
    # SELECT-prefixed but contains a DELETE clause
    "SELECT * WHERE { ?s ?p ?o } ; DELETE WHERE { ?s ?p ?o }",
])
def test_sparql_endpoint_rejects_mutation(payload):
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/sparql", params={"query": payload})
    assert r.status_code == 403, f"payload {payload!r} should be 403, got {r.status_code}"


def test_sparql_endpoint_rejects_oversized_query():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    big = "SELECT * WHERE { ?s ?p ?o } # " + ("x" * 10_000)
    r = client.get("/api/sparql", params={"query": big})
    assert r.status_code == 413
