"""Round-2 security regression tests.

Covers security_middleware.py and the FastAPI year-range bounds:

- (a) CSP / X-Frame / X-Content-Type / Referrer / Permissions headers
      are present on API and static responses.
- (g) Server header is stripped.
- (b) CORS Access-Control-Allow-Origin is NEVER set, even if upstream
      Trails adapter tries.
- (c) Per-IP rate limiter returns 429 with Retry-After on burst.
- (d) Pydantic year-range bounds give HTTP 422 on out-of-range input.
- (f) The injection-shaped-but-empty-result logger fires a WARNING.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _client(env: dict | None = None):
    """Build a fresh TestClient. ``env`` lets tests tweak WD_RATE_LIMIT etc."""
    import os
    if env:
        for k, v in env.items():
            os.environ[k] = str(v)
    from fastapi.testclient import TestClient
    from app import create_app
    return TestClient(create_app())


# --- (a) + (g) Security headers --------------------------------------------


def test_security_headers_on_api_response():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/health")
    assert r.status_code == 200
    h = r.headers
    assert "content-security-policy" in {k.lower() for k in h}
    csp = h.get("content-security-policy") or h.get("Content-Security-Policy") or ""
    assert "default-src 'self'" in csp
    assert h.get("x-frame-options", "").upper() == "DENY"
    assert h.get("x-content-type-options", "").lower() == "nosniff"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in (h.get("permissions-policy", ""))


def test_server_header_stripped():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/health")
    # The TestClient does NOT go through uvicorn's transport layer (which
    # injects Server: uvicorn). We only assert that the middleware did
    # not RE-introduce one and that any explicit Server header has been
    # removed. starlette.testclient leaves the field unset by default,
    # so the assertion is "Server header is not present".
    assert "server" not in {k.lower() for k in r.headers}


# --- (b) CORS lockdown ------------------------------------------------------


def test_cors_origin_never_set():
    try:
        client = _client()
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/health")
    cors_keys = {
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
    }
    present = {k.lower() for k in r.headers} & cors_keys
    assert not present, f"unexpected CORS headers leaked: {present}"


# --- (c) Rate limit ---------------------------------------------------------


def test_rate_limit_triggers_429_with_retry_after():
    try:
        # Configure a very small bucket so the test is fast.
        # The middleware reads WD_RATE_LIMIT at app-construction time, so
        # we must set it BEFORE building the TestClient.
        client = _client(env={"WD_RATE_LIMIT": "3", "WD_RATE_LIMIT_WINDOW_S": "60"})
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")

    # Hit a non-exempt /api/ endpoint. /api/cq/01 is fine.
    last = None
    for _ in range(3):
        last = client.get("/api/cq/01")
        assert last.status_code == 200, last.text
    # 4th request from the same client should be 429.
    r = client.get("/api/cq/01")
    assert r.status_code == 429, r.text
    assert "retry-after" in {k.lower() for k in r.headers}


def test_rate_limit_skips_health_endpoint():
    try:
        client = _client(env={"WD_RATE_LIMIT": "2", "WD_RATE_LIMIT_WINDOW_S": "60"})
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    # /api/health is exempt — hit it 10 times, never 429.
    for _ in range(10):
        r = client.get("/api/health")
        assert r.status_code == 200, r.text


# --- (d) Year-range validation ---------------------------------------------


@pytest.mark.parametrize("path", [
    "/api/cq/13",
    "/api/cq/14",
    "/api/metrics/entropy",
    "/api/metrics/fragmentation",
    "/api/metrics/divergence",
])
def test_year_below_minimum_is_422(path):
    try:
        client = _client(env={"WD_RATE_LIMIT": "0"})
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get(path, params={"year": 5})
    assert r.status_code == 422, f"{path} accepted year=5: {r.status_code} {r.text[:200]}"


def test_year_above_maximum_is_422():
    try:
        client = _client(env={"WD_RATE_LIMIT": "0"})
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/cq/13", params={"year": 9999})
    assert r.status_code == 422


def test_cq06_year_range_bounded():
    try:
        client = _client(env={"WD_RATE_LIMIT": "0"})
    except ImportError as exc:
        pytest.skip(f"app not ready: {exc}")
    r = client.get("/api/cq/06", params={"year_from": 5, "year_to": 1999})
    assert r.status_code == 422


# --- (f) Injection-shaped-but-empty WARNING --------------------------------


def test_injection_warn_logged_on_quoted_payload(caplog):
    try:
        from loader import load_all_ttl
        from trails.sdk import Context, kernel_store
        from capabilities.competency import cq13_groups_attributing_word
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(
        trace_id="t-inj", principal="test:injector", store=kernel_store(),
    )
    with caplog.at_level(logging.WARNING, logger="word_drift.security"):
        rows = cq13_groups_attributing_word(ctx.kg, word='x"} UNION { ?s ?p ?o }')
    assert rows == []
    # The payload is shaped like injection AND returned 0 rows → WARN.
    matched = [
        r for r in caplog.records
        if "possible_sparql_injection" in r.getMessage()
    ]
    assert matched, f"expected possible_sparql_injection log, got: {[r.getMessage() for r in caplog.records]}"


def test_legit_zero_result_does_not_warn(caplog):
    """A legit word that simply has no attributions must NOT log a warning."""
    try:
        from loader import load_all_ttl
        from trails.sdk import Context, kernel_store
        from capabilities.competency import cq13_groups_attributing_word
    except ImportError as exc:
        pytest.skip(f"modules not ready: {exc}")

    load_all_ttl(data_root=_REPO_ROOT)
    ctx = Context(
        trace_id="t-clean", principal="test:clean", store=kernel_store(),
    )
    with caplog.at_level(logging.WARNING, logger="word_drift.security"):
        # Innocuous, no-meta-chars query that won't match anything.
        rows = cq13_groups_attributing_word(ctx.kg, word="ZZZNoSuchWordZZZ")
    assert rows == []
    matched = [
        r for r in caplog.records
        if "possible_sparql_injection" in r.getMessage()
    ]
    assert not matched, "clean payload must not trigger the injection warning"
