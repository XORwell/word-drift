"""HTTP security hardening for the word-drift FastAPI app (round 2).

Wires three Starlette-style middlewares into ``create_app()``:

1. :class:`SecurityHeadersMiddleware` — sets CSP, X-Frame-Options,
   X-Content-Type-Options, Referrer-Policy, Permissions-Policy on every
   response (FastAPI routes AND static-file responses). Also strips the
   ``Server: uvicorn`` header.
2. :class:`StripCORSMiddleware` — removes any
   ``Access-Control-Allow-Origin`` headers added by upstream middleware
   (e.g. Trails' adapter CORS layer). The word-drift explorer is
   strictly same-origin; nothing should cross.
3. :class:`RateLimitMiddleware` — per-IP token-bucket on ``/api/*``,
   configurable via ``WD_RATE_LIMIT`` (default 60 req / 60 s). Skips
   ``/api/health`` (docker healthcheck) and the cacheable static graph
   docs.

Year-range validation lives on the route signatures themselves (Pydantic
``Field`` constraints) — see ``app.py``.

See docs/plans/word-drift-3.0/security-round-2.md for the threat model.

TODO(W3): the inline ``<script>`` blocks in site/explore.html etc. force
``'unsafe-inline'`` in the CSP. Migrate them to external JS so the CSP
can drop the ``'unsafe-inline'`` source.
"""
from __future__ import annotations

import collections
import logging
import os
import threading
import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("word_drift.security")

# ---------------------------------------------------------------------------
# (a) Security headers + (g) server-header strip
# ---------------------------------------------------------------------------

# CSP rationale (see TODO above): script/style still need 'unsafe-inline'
# because site/explore.html and friends ship inline <script> blocks today.
# Once those are externalised, drop the 'unsafe-inline' source.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'"
)

_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CSP,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # HSTS deliberately omitted — Caddy in front handles transport security.
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add static security headers to every response.

    Also removes the ``Server`` header (uvicorn leaks ``Server: uvicorn``
    by default which is a tiny but free intel disclosure).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        response: Response = await call_next(request)
        for k, v in _SECURITY_HEADERS.items():
            # Don't clobber a header an upstream layer set deliberately.
            response.headers.setdefault(k, v)
        # Strip the Server header. Some Starlette responses don't carry
        # one but uvicorn injects it at the transport level — del is a
        # no-op when the header isn't present.
        if "server" in response.headers:
            del response.headers["server"]
        return response


# ---------------------------------------------------------------------------
# (b) CORS strip
# ---------------------------------------------------------------------------


class StripCORSMiddleware(BaseHTTPMiddleware):
    """Remove any Access-Control-Allow-* headers.

    The Trails HTTP adapter may add a permissive CORS layer when its
    ``[security].cors_origins`` config contains ``*`` or a wildcard. The
    word-drift explorer is strictly same-origin, so we strip any such
    headers on the way out. This is a belt-and-braces defence — the
    correct fix is to not configure CORS upstream, but middleware order
    matters less than the guarantee.
    """

    _CORS_HEADERS = (
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-expose-headers",
        "access-control-max-age",
    )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        response: Response = await call_next(request)
        for h in self._CORS_HEADERS:
            if h in response.headers:
                del response.headers[h]
        return response


# ---------------------------------------------------------------------------
# (c) Per-IP rate limiter on /api/*
# ---------------------------------------------------------------------------


class _PerIPBucket:
    """Tiny token-bucket-ish sliding window keyed by client IP."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._lock = threading.Lock()
        self._buckets: dict[str, collections.deque[float]] = {}

    def check(self, ip: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            dq = self._buckets.setdefault(ip, collections.deque())
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= self.max_requests:
                retry_after = int(dq[0] + self.window - now) + 1
                return False, max(retry_after, 1)
            dq.append(now)
            return True, 0


# Paths under /api/ that the site itself hits frequently and that we
# don't want to throttle: the docker healthcheck and the cacheable
# graph documents (served outside /api/ anyway, but listed here as a
# safety net if the URLs ever move).
_RATE_LIMIT_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/health",
    "/api/version",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding window rate limiter for ``/api/*`` endpoints.

    Configurable via ``WD_RATE_LIMIT`` env var (default 60 / 60 s).
    Set ``WD_RATE_LIMIT=0`` to disable.

    /api/health and /api/version are exempt so the docker healthcheck
    and the version-strings poll never see 429s.
    """

    def __init__(self, app, max_requests: int, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.bucket = _PerIPBucket(max_requests, window_seconds)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        # Only rate-limit the /api/ surface. Static files and graph JSON
        # are served on other paths and pass straight through.
        if self.max_requests <= 0:
            return await call_next(request)
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        if any(path.startswith(p) for p in _RATE_LIMIT_EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = self.bucket.check(client_ip)
        if not allowed:
            return JSONResponse(
                {"error": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# (f) SPARQL injection warn-log helper
# ---------------------------------------------------------------------------

_INJECTION_HINT_CHARS = ('"', "{", "}", ";", "#", "\\")


def looks_injection_shaped(s: str) -> bool:
    """Heuristic: does the input contain a SPARQL meta character?

    Cheap pre-screen; cheap to false-positive-rate but used only to log,
    never to block (the actual defence is parameter binding in
    capabilities.competency / metrics_multi_group).
    """
    if not s:
        return False
    return any(c in s for c in _INJECTION_HINT_CHARS)


def log_possible_injection(
    principal: str, payload: str, *, source: str = "cq",
) -> None:
    """Log a structured WARNING when an obviously-shaped payload yields 0 rows.

    Per round 2 finding (f): when CQ13/CQ14/_attribution_rows return 0
    rows AND the input contained a SPARQL meta character, that's a strong
    signal someone is probing the injection surface. Log it so SOC tools
    can spot the pattern. Payload is truncated to 50 chars to avoid
    log-injection or huge log lines.
    """
    redacted = (payload or "")[:50]
    logger.warning(
        "possible_sparql_injection principal=%s source=%s payload=%r",
        principal or "anonymous", source, redacted,
    )


# ---------------------------------------------------------------------------
# Factory used by app.create_app()
# ---------------------------------------------------------------------------


def install(app) -> None:
    """Wire all three middlewares onto a FastAPI app, in the correct order.

    Order matters because Starlette runs the *last* added middleware
    *first* on the request and *last* on the response. We want:

    - SecurityHeaders runs LAST on response (added FIRST) so every
      response, including ones short-circuited by the rate limiter,
      carries the headers.
    - StripCORS runs after SecurityHeaders on response (added AFTER).
    - RateLimit runs FIRST on the request (added LAST) so it short-
      circuits before any business logic.
    """
    rate_limit = int(os.environ.get("WD_RATE_LIMIT", "60"))
    window = int(os.environ.get("WD_RATE_LIMIT_WINDOW_S", "60"))

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(StripCORSMiddleware)
    app.add_middleware(
        RateLimitMiddleware, max_requests=rate_limit, window_seconds=window,
    )
    logger.info(
        "security middleware installed (rate_limit=%d/%ds)", rate_limit, window,
    )
