"""W9 — Round-3 production hardening regression tests.

Covers:
- W5: ``/graph-distribution.json`` is cached at bootstrap; the second
  request issues ~0 SPARQL queries (drop >= 90% versus the first ~50).
- F2: ``metric_timeline`` is internally one SPARQL fetch + Python partition.
  Same numeric output as the legacy implementation (regression fixture).
- F4: ``Cache-Control`` header is present on ``/assets/*`` static
  responses; deliberately absent (or no-store-shaped) on ``/api/*`` and
  on HTML pages so deploys propagate immediately.
- W6: ``/api/version`` no longer exposes ``commit`` by default; only when
  ``WD_VERSION_EXPOSE_COMMIT=1`` is set.
- CSP: ``Content-Security-Policy`` no longer contains ``'unsafe-inline'``
  in the ``script-src`` directive (the last inline blocks were removed).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client(env: dict | None = None):
    """Build a TestClient. Always sets WD_RATE_LIMIT=0 to keep the suite quick.

    Note: app.py module-level state (capability registry, cached
    distribution doc) is preserved across tests on purpose — reloading
    the module would re-register @capability decorators and explode. The
    version cache is the only env-gated cache that matters, and it lives
    inside ``create_app()`` as a fresh closure on every call, so env-var
    flips between tests still take effect.
    """
    base = {"WD_RATE_LIMIT": "0"}
    if env:
        base.update({k: str(v) for k, v in env.items()})
    for k, v in base.items():
        os.environ[k] = v
    try:
        from fastapi.testclient import TestClient
        from app import create_app
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    return TestClient(create_app())


class _QueryCounter:
    """Best-effort monkey-patch of ``trails.sdk.KG.query`` that counts calls."""

    def __init__(self) -> None:
        self.count = 0
        self._original = None
        self._patched_cls = None

    def __enter__(self):
        try:
            from trails.sdk import KG  # type: ignore
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"trails KG not importable: {exc}")
        self._patched_cls = KG
        self._original = KG.query

        counter = self

        def counted_query(self_kg, sparql, *args, **kwargs):
            counter.count += 1
            return counter._original(self_kg, sparql, *args, **kwargs)

        KG.query = counted_query  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._patched_cls is not None and self._original is not None:
            self._patched_cls.query = self._original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# W5: graph-distribution.json cache hit drops query count >= 90%
# ---------------------------------------------------------------------------


def test_graph_distribution_second_request_drops_query_count():
    """After bootstrap, the endpoint serves from cache — no fresh SPARQL run."""
    client = _client()
    # Warm-up: trigger a request so the app is fully wired. Bootstrap (and
    # the cached _graph_distribution build) ran during create_app(), so any
    # queries the FIRST request fires are NOT the ~50 distribution queries.
    r0 = client.get("/api/health")
    assert r0.status_code == 200, r0.text

    with _QueryCounter() as q:
        r1 = client.get("/graph-distribution.json")
    assert r1.status_code == 200, r1.text
    first_count = q.count

    with _QueryCounter() as q2:
        r2 = client.get("/graph-distribution.json")
    assert r2.status_code == 200, r2.text
    second_count = q2.count

    # The cached response must issue zero SPARQL queries.
    assert second_count == 0, (
        f"cache hit must not query the store; got {second_count} queries"
    )
    # Conservative drop check (handles the edge case where both = 0 already
    # because bootstrap ran before the patch: in that case first_count is
    # already 0 and the "drop" is trivially satisfied).
    if first_count > 0:
        ratio = (first_count - second_count) / first_count
        assert ratio >= 0.9, (
            f"expected >=90% drop, got first={first_count} second={second_count}"
        )


def test_graph_distribution_refresh_requires_admin_token():
    """``?refresh=1`` without the admin env var is rejected with 403."""
    os.environ.pop("WD_DEV_ADMIN_TOKEN", None)
    client = _client()
    r = client.get("/graph-distribution.json", params={"refresh": 1})
    assert r.status_code == 403, r.text


def test_graph_distribution_refresh_with_correct_token_rebuilds():
    """``?refresh=1&token=…`` matches WD_DEV_ADMIN_TOKEN and returns 200."""
    client = _client(env={"WD_DEV_ADMIN_TOKEN": "sekret-w9"})
    r = client.get(
        "/graph-distribution.json",
        params={"refresh": 1, "token": "sekret-w9"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "words" in body, body
    assert "meta" in body, body


# ---------------------------------------------------------------------------
# F2: metric_timeline N+1 → 1 query
# ---------------------------------------------------------------------------


def test_metric_timeline_uses_single_attribution_fetch():
    """The new implementation hits ``_attribution_rows`` once per word."""
    try:
        from loader import load_all_ttl
        from trails.sdk import Context, kernel_store
        from capabilities.metrics_multi_group import metric_timeline
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(
        trace_id="t-w9-timeline", principal="system:test", store=kernel_store(),
    )

    with _QueryCounter() as q:
        tl = metric_timeline(ctx.kg, word="Querdenker")

    assert isinstance(tl, list)
    assert len(tl) >= 1, "Querdenker fixture must produce at least one year"
    # The legacy implementation queried _attribution_rows for the year list
    # then re-queried (entropy + fragmentation + group divergence +
    # platform divergence) × N years — so ~ 1 + 4N queries (~21 for 5 yrs).
    # The new implementation pulls rows ONCE and partitions in Python.
    assert q.count <= 3, (
        f"metric_timeline must issue at most a small constant number of "
        f"queries (target 1, allow up to 3 for safety); got {q.count}"
    )


def test_metric_timeline_numeric_output_matches_year_by_year_recompute():
    """Refactored timeline must equal a year-by-year recompute of each metric.

    This protects against the partition-by-year approach silently dropping
    rows (e.g., rows without an atYear, year-coercion errors).
    """
    try:
        from loader import load_all_ttl
        from trails.sdk import Context, kernel_store
        from capabilities.metrics_multi_group import (
            metric_timeline, semantic_entropy, semantic_fragmentation_index,
            group_divergence, cross_platform_distance,
        )
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(
        trace_id="t-w9-tl-eq", principal="system:test", store=kernel_store(),
    )

    tl = metric_timeline(ctx.kg, word="Querdenker")
    for row in tl:
        y = row["year"]
        ent = semantic_entropy(ctx.kg, word="Querdenker", year=y)
        frag = semantic_fragmentation_index(ctx.kg, word="Querdenker", year=y)
        div = group_divergence(ctx.kg, word="Querdenker", year=y)
        plat = cross_platform_distance(ctx.kg, word="Querdenker", year=y)

        def _close(a: Any, b: Any) -> bool:
            if a is None and b is None:
                return True
            if a is None or b is None:
                return False
            return abs(float(a) - float(b)) < 1e-9

        assert _close(row["entropy"], ent.get("value")), (row, ent)
        assert _close(row["fragmentation"], frag.get("value")), (row, frag)
        assert _close(row["divergence_max"], div.get("max")), (row, div)
        assert _close(row["divergence_mean"], div.get("mean")), (row, div)
        assert _close(row["platform_divergence_max"], plat.get("max")), (row, plat)
        assert _close(row["platform_divergence_mean"], plat.get("mean")), (row, plat)


# ---------------------------------------------------------------------------
# F4: Cache-Control on /assets/* but NOT on HTML/API
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [
    "/assets/explore.css",
    "/assets/views/distribution.js",
])
def test_cache_control_present_on_static_assets(path):
    client = _client()
    r = client.get(path)
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
    cc = r.headers.get("cache-control") or r.headers.get("Cache-Control") or ""
    assert "max-age" in cc.lower(), f"missing Cache-Control on {path}: {cc!r}"
    assert "must-revalidate" in cc.lower(), (
        f"Cache-Control must include must-revalidate on {path}: {cc!r}"
    )


@pytest.mark.parametrize("path", [
    "/api/health",
    "/explore.html",
])
def test_cache_control_absent_or_nostore_on_html_and_api(path):
    client = _client()
    r = client.get(path)
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
    cc = (
        r.headers.get("cache-control") or r.headers.get("Cache-Control") or ""
    ).lower()
    # Either absent entirely, or explicitly no-store. Anything with a
    # max-age would defeat the "deploys propagate immediately" guarantee.
    if cc:
        assert "no-store" in cc or "max-age=0" in cc, (
            f"{path} must not carry a positive max-age; got Cache-Control={cc!r}"
        )


# ---------------------------------------------------------------------------
# W6: commit hash opt-in on /api/version
# ---------------------------------------------------------------------------


def test_api_version_omits_commit_by_default():
    os.environ.pop("WD_VERSION_EXPOSE_COMMIT", None)
    client = _client()
    r = client.get("/api/version")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "commit" not in body, (
        f"commit hash must be opt-in via WD_VERSION_EXPOSE_COMMIT; "
        f"got body keys = {sorted(body.keys())}"
    )


def test_api_version_exposes_commit_when_opted_in():
    client = _client(env={"WD_VERSION_EXPOSE_COMMIT": "1"})
    r = client.get("/api/version")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "commit" in body, (
        f"WD_VERSION_EXPOSE_COMMIT=1 must surface the commit field; "
        f"got body keys = {sorted(body.keys())}"
    )


# ---------------------------------------------------------------------------
# CSP: 'unsafe-inline' removed from script-src
# ---------------------------------------------------------------------------


def test_csp_script_src_no_unsafe_inline():
    client = _client()
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    csp = (
        r.headers.get("content-security-policy")
        or r.headers.get("Content-Security-Policy")
        or ""
    )
    assert csp, "CSP header must be present"
    # Extract the script-src directive specifically; other directives may
    # still legitimately carry 'unsafe-inline' (e.g. style-src until the
    # inline <style> blocks on downloads.html are externalised).
    directives = {}
    for chunk in csp.split(";"):
        parts = chunk.strip().split()
        if not parts:
            continue
        directives[parts[0].lower()] = " ".join(parts[1:])
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" not in script_src, (
        f"script-src must not include 'unsafe-inline'; got: {script_src!r}"
    )
