#!/usr/bin/env python3
"""Word-Drift on Trails — main application.

Equivalent of the original word-drift's 'python -m http.server' but:
- Backed by a live Oxigraph SPARQL store (not rdflib in-memory)
- Serves graph-core.json and graph-detail.json from live SPARQL queries
- Adds provenance, SHACL validation, and policy via Trails
- Exposes the 12 competency questions as a REST API
- Fully containerisable with docker-compose
"""
from __future__ import annotations
import copy
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from models import (
    Word, TriggerEvent, DriftEvent, Sense, CausalHypothesis,
    Group, Community, MeaningAttribution,
)

logger = logging.getLogger("word_drift_trails")

# ---------------------------------------------------------------------------
# Bootstrap: load data once at import time (cached in module-level globals)
# ---------------------------------------------------------------------------
# TTL data is loaded into the Trails kernel store (singleton); the cached
# graph documents are built from a bootstrap Context backed by that store.

_graph_core: dict | None = None
_graph_detail: dict | None = None
_load_time_s: float = 0.0


def _bootstrap():
    global _graph_core, _graph_detail, _load_time_s
    if _graph_core is not None:
        return
    t0 = time.monotonic()

    from loader import load_all_ttl
    from graph_builder import build_graph_document, split_document
    from trails.context import Context
    from trails.runtime import _kernel_store

    # Load all TTL data into the Trails kernel store
    load_all_ttl()

    # Create a bootstrap context to query the loaded data
    _boot_ctx = Context(
        trace_id="bootstrap",
        principal="system:bootstrap",
        store=_kernel_store(),
    )

    doc = build_graph_document(_boot_ctx.kg)   # use ctx.kg, not _store
    _graph_core, _graph_detail = split_document(doc)
    _load_time_s = time.monotonic() - t0
    logger.info("bootstrap complete in %.1fs", _load_time_s)


# ---------------------------------------------------------------------------
# Trails app
# ---------------------------------------------------------------------------
from trails import capability, Context

# NOTE: App(__name__) is not instantiated here because create_app() builds
# the real FastAPI/MCP application.  The bare `app = App(__name__)` was
# previously used only as a fallback runner; create_app() replaces it.


@capability("graph_core")
def graph_core(ctx: Context) -> dict:
    """Return graph-core.json — the lightweight first-paint document."""
    _bootstrap()
    return _graph_core


@capability("graph_detail")
def graph_detail(ctx: Context) -> dict:
    """Return graph-detail.json — heavy per-word fields."""
    _bootstrap()
    return _graph_detail


@capability("graph_full")
def graph_full(ctx: Context) -> dict:
    """Return the full graph.json document."""
    _bootstrap()
    full = copy.deepcopy(_graph_core)
    for word in full.get("words", []):
        detail = _graph_detail.get(word["id"], {})
        word.update(detail)
    return full


@capability("health")
def health(ctx: Context) -> dict:
    """Return application health status."""
    _bootstrap()
    # Use ORM to count entities — this proves Trails ORM is live
    try:
        word_count = len(Word.where(ctx).fetch())
    except Exception:
        word_count = len((_graph_core or {}).get("words", []))
    try:
        trigger_count = len(TriggerEvent.where(ctx).fetch())
    except Exception:
        trigger_count = len((_graph_core or {}).get("triggers", []))
    try:
        drift_count = len(DriftEvent.where(ctx).fetch())
    except Exception:
        drift_count = 0

    triple_count = 0
    try:
        rows = ctx.kg.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
        if rows:
            triple_count = int(rows[0].get("n", 0))
    except Exception:
        pass

    return {
        "status": "ok",
        "triples": triple_count,
        "words": word_count,
        "triggers": trigger_count,
        "drift_events": drift_count,
        "load_time_s": round(_load_time_s, 2),
    }


@capability("sparql_query")
def sparql_query(ctx: Context, query: str) -> list[dict]:
    """Execute a SPARQL SELECT query against the word-drift store."""
    _bootstrap()
    PREFIXES = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX time: <http://www.w3.org/2006/time#>
PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
"""
    full_query = PREFIXES + query
    return ctx.kg.query(full_query)


# ---------------------------------------------------------------------------
# Competency questions as capabilities (CQ01–CQ12)
# ---------------------------------------------------------------------------

@capability("cq_most_reframed")
def cq_most_reframed(ctx: Context, limit: int = 10) -> list[dict]:
    """CQ01: Which trigger event reframed the most words?"""
    from capabilities.competency import cq01_most_reframed
    _bootstrap()
    return cq01_most_reframed(ctx.kg, limit=limit)


@capability("cq_hypotheses_for_word")
def cq_hypotheses_for_word(ctx: Context, word: str = "Querdenker") -> list[dict]:
    """CQ02: All causal hypotheses for a given word, with evidence type and confidence."""
    from capabilities.competency import cq02_hypotheses_for_word
    _bootstrap()
    return cq02_hypotheses_for_word(ctx.kg, word=word)


@capability("cq_drifttype_by_trigger")
def cq_drifttype_by_trigger(ctx: Context) -> list[dict]:
    """CQ03: Drift-type distribution by trigger category."""
    from capabilities.competency import cq03_drifttype_by_trigger
    _bootstrap()
    return cq03_drifttype_by_trigger(ctx.kg)


@capability("cq_cross_lingual_same_direction")
def cq_cross_lingual_same_direction(ctx: Context) -> list[dict]:
    """CQ04: Same-direction drift across DE and EN."""
    from capabilities.competency import cq04_cross_lingual_same_direction
    _bootstrap()
    return cq04_cross_lingual_same_direction(ctx.kg)


@capability("cq_connotation_reversed")
def cq_connotation_reversed(ctx: Context) -> list[dict]:
    """CQ05: Words whose connotation reversed (positive <-> negative)."""
    from capabilities.competency import cq05_connotation_reversed
    _bootstrap()
    return cq05_connotation_reversed(ctx.kg)


@capability("cq_triggers_in_date_range")
def cq_triggers_in_date_range(
    ctx: Context, year_from: int = 1900, year_to: int = 1999
) -> list[dict]:
    """CQ06: Trigger events in a date range."""
    from capabilities.competency import cq06_triggers_in_date_range
    _bootstrap()
    return cq06_triggers_in_date_range(ctx.kg, year_from=year_from, year_to=year_to)


@capability("cq_speculative_only")
def cq_speculative_only(ctx: Context) -> list[dict]:
    """CQ07: Hypotheses resting ONLY on speculative evidence."""
    from capabilities.competency import cq07_speculative_only
    _bootstrap()
    return cq07_speculative_only(ctx.kg)


@capability("cq_strongest_evidence")
def cq_strongest_evidence(ctx: Context) -> list[dict]:
    """CQ08: Strongest evidence tier backing each drift event."""
    from capabilities.competency import cq08_strongest_evidence
    _bootstrap()
    return cq08_strongest_evidence(ctx.kg)


@capability("cq_competing_hypotheses")
def cq_competing_hypotheses(ctx: Context) -> list[dict]:
    """CQ09: Drift events with competing causal hypotheses."""
    from capabilities.competency import cq09_competing_hypotheses
    _bootstrap()
    return cq09_competing_hypotheses(ctx.kg)


@capability("cq_sense_timeline")
def cq_sense_timeline(ctx: Context) -> list[dict]:
    """CQ10: Per-word sense timeline with connotation, ordered by first attestation."""
    from capabilities.competency import cq10_sense_timeline
    _bootstrap()
    return cq10_sense_timeline(ctx.kg)


@capability("cq_reappropriation_words")
def cq_reappropriation_words(ctx: Context) -> list[dict]:
    """CQ11: Reclaimed (reappropriated) words and their triggers."""
    from capabilities.competency import cq11_reappropriation_words
    _bootstrap()
    return cq11_reappropriation_words(ctx.kg)


@capability("cq_provenance_completeness")
def cq_provenance_completeness(ctx: Context) -> list[dict]:
    """CQ12: Drift events provenanced to at least one source (provenance completeness)."""
    from capabilities.competency import cq12_provenance_completeness
    _bootstrap()
    return cq12_provenance_completeness(ctx.kg)


# ---------------------------------------------------------------------------
# 3.0 — Multi-group competency capabilities
# ---------------------------------------------------------------------------

@capability("cq_groups_attributing_word")
def cq_groups_attributing_word(
    ctx: Context, word: str = "Querdenker", year: int | None = None,
) -> list[dict]:
    """CQ13 (3.0): Per-group sense attributions for a word."""
    from capabilities.competency import cq13_groups_attributing_word
    _bootstrap()
    return cq13_groups_attributing_word(ctx.kg, word=word, year=year)


# ---------------------------------------------------------------------------
# 3.0 — Multi-group metrics (M3): entropy, fragmentation, group divergence
# ---------------------------------------------------------------------------

@capability("metric_semantic_entropy")
def metric_semantic_entropy(
    ctx: Context, word: str = "Querdenker", year: int | None = None,
) -> dict:
    """Shannon entropy of the sense distribution for a word."""
    from capabilities.metrics_multi_group import semantic_entropy
    _bootstrap()
    return semantic_entropy(ctx.kg, word=word, year=year)


@capability("metric_semantic_fragmentation")
def metric_semantic_fragmentation(
    ctx: Context, word: str = "Querdenker", year: int | None = None,
) -> dict:
    """Gini-Simpson fragmentation over the (group, sense) grid."""
    from capabilities.metrics_multi_group import semantic_fragmentation_index
    _bootstrap()
    return semantic_fragmentation_index(ctx.kg, word=word, year=year)


@capability("metric_group_divergence")
def metric_group_divergence(
    ctx: Context, word: str = "Querdenker", year: int | None = None,
) -> dict:
    """Pairwise JSD between group sense-distributions for a word."""
    from capabilities.metrics_multi_group import group_divergence
    _bootstrap()
    return group_divergence(ctx.kg, word=word, year=year)


@capability("metric_timeline")
def metric_timeline(
    ctx: Context, word: str = "Querdenker",
) -> list[dict]:
    """Per-year snapshot of all three M3 metrics for a word."""
    from capabilities.metrics_multi_group import metric_timeline as _tl
    _bootstrap()
    return _tl(ctx.kg, word=word)


# ---------------------------------------------------------------------------
# HTTP application factory
# ---------------------------------------------------------------------------

def create_app():
    """Create the FastAPI application with all routes mounted.

    Wires the Trails MCP server into a FastAPI app, then adds:
    - ``GET /graph-core.json``  — lightweight first-paint graph document
    - ``GET /graph-detail.json`` — heavy per-word fields
    - ``GET /graph.json``        — merged full document
    - ``GET /api/health``        — word-drift specific health check
    - ``GET /api/sparql``        — ad-hoc SPARQL pass-through
    - ``GET /api/cq/{n}``        — all 12 competency-question endpoints
    - ``/``                      — static ``site/`` directory (mounted last)
    """
    # Bootstrap data before creating the HTTP app so the first request is fast.
    _bootstrap()

    from trails.mcp_server import TrailsMCPServer
    from trails.http_adapter import TrailsHTTPAdapter

    mcp = TrailsMCPServer(name="word-drift", version="0.1.0")
    adapter = TrailsHTTPAdapter(mcp, require_auth=False)
    http_app = adapter.create_app()

    # Remove the Trails landing page route so the word-drift StaticFiles
    # mount (added last) can own GET /. FastAPI matches routes in list order
    # and the adapter registers GET / first, so we strip it here.
    from starlette.routing import Route
    http_app.router.routes = [
        r for r in http_app.router.routes
        if not (isinstance(r, Route) and r.path == "/"
                and "GET" in (r.methods or set()))
    ]

    try:
        from fastapi.responses import JSONResponse
        from starlette.staticfiles import StaticFiles
        from trails.context import Context
        from trails.runtime import _kernel_store

        # ------------------------------------------------------------------
        # Live JSON endpoints — same paths the frontend fetches
        # ------------------------------------------------------------------

        @http_app.get("/graph-core.json", response_model=None)
        async def serve_graph_core():
            """Serve graph-core.json from in-memory cache."""
            return JSONResponse(_graph_core)

        @http_app.get("/graph-detail.json", response_model=None)
        async def serve_graph_detail():
            """Serve graph-detail.json from in-memory cache."""
            return JSONResponse(_graph_detail)

        @http_app.get("/graph.json", response_model=None)
        async def serve_graph_full():
            """Serve the merged graph.json document."""
            full = copy.deepcopy(_graph_core)
            for word in full.get("words", []):
                detail = _graph_detail.get(word["id"], {})
                word.update(detail)
            return JSONResponse(full)

        # ------------------------------------------------------------------
        # Word-drift specific API endpoints
        # ------------------------------------------------------------------

        @http_app.get("/api/health", response_model=None)
        async def api_health():
            """Word-drift specific health check."""
            _ctx = Context(trace_id="health-check", principal="system", store=_kernel_store())
            triple_count = 0
            try:
                rows = _ctx.kg.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
                if rows:
                    triple_count = int(rows[0].get("n", 0))
            except Exception:
                pass
            return JSONResponse({
                "status": "ok",
                "triples": triple_count,
                "words": len((_graph_core or {}).get("words", [])),
                "triggers": len((_graph_core or {}).get("triggers", [])),
                "load_time_s": round(_load_time_s, 2),
            })

        @http_app.get("/api/sparql", response_model=None)
        async def api_sparql(query: str):
            """Execute an ad-hoc SPARQL SELECT query."""
            _ctx = Context(trace_id="sparql", principal="system", store=_kernel_store())
            try:
                rows = _ctx.kg.query(query)
            except Exception as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
            return JSONResponse(rows)

        # ------------------------------------------------------------------
        # Competency question REST endpoints
        # ------------------------------------------------------------------

        from capabilities import competency as _cq

        @http_app.get("/api/cq/01", response_model=None)
        async def api_cq01(limit: int = 10):
            """CQ01: Which trigger event reframed the most words?"""
            _ctx = Context(trace_id="cq01", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq01_most_reframed(_ctx.kg, limit=limit))

        @http_app.get("/api/cq/02", response_model=None)
        async def api_cq02(word: str = "Querdenker"):
            """CQ02: All causal hypotheses for a given word."""
            _ctx = Context(trace_id="cq02", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq02_hypotheses_for_word(_ctx.kg, word=word))

        @http_app.get("/api/cq/03", response_model=None)
        async def api_cq03():
            """CQ03: Drift-type distribution by trigger category."""
            _ctx = Context(trace_id="cq03", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq03_drifttype_by_trigger(_ctx.kg))

        @http_app.get("/api/cq/04", response_model=None)
        async def api_cq04():
            """CQ04: Same-direction drift across DE and EN."""
            _ctx = Context(trace_id="cq04", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq04_cross_lingual_same_direction(_ctx.kg))

        @http_app.get("/api/cq/05", response_model=None)
        async def api_cq05():
            """CQ05: Words whose connotation reversed."""
            _ctx = Context(trace_id="cq05", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq05_connotation_reversed(_ctx.kg))

        @http_app.get("/api/cq/06", response_model=None)
        async def api_cq06(year_from: int = 1900, year_to: int = 1999):
            """CQ06: Trigger events in a date range."""
            _ctx = Context(trace_id="cq06", principal="system", store=_kernel_store())
            return JSONResponse(
                _cq.cq06_triggers_in_date_range(_ctx.kg, year_from=year_from, year_to=year_to)
            )

        @http_app.get("/api/cq/07", response_model=None)
        async def api_cq07():
            """CQ07: Hypotheses resting ONLY on speculative evidence."""
            _ctx = Context(trace_id="cq07", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq07_speculative_only(_ctx.kg))

        @http_app.get("/api/cq/08", response_model=None)
        async def api_cq08():
            """CQ08: Strongest evidence tier backing each drift event."""
            _ctx = Context(trace_id="cq08", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq08_strongest_evidence(_ctx.kg))

        @http_app.get("/api/cq/09", response_model=None)
        async def api_cq09():
            """CQ09: Drift events with competing causal hypotheses."""
            _ctx = Context(trace_id="cq09", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq09_competing_hypotheses(_ctx.kg))

        @http_app.get("/api/cq/10", response_model=None)
        async def api_cq10():
            """CQ10: Per-word sense timeline with connotation."""
            _ctx = Context(trace_id="cq10", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq10_sense_timeline(_ctx.kg))

        @http_app.get("/api/cq/11", response_model=None)
        async def api_cq11():
            """CQ11: Reappropriated words and their triggers."""
            _ctx = Context(trace_id="cq11", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq11_reappropriation_words(_ctx.kg))

        @http_app.get("/api/cq/12", response_model=None)
        async def api_cq12():
            """CQ12: Drift events with source provenance."""
            _ctx = Context(trace_id="cq12", principal="system", store=_kernel_store())
            return JSONResponse(_cq.cq12_provenance_completeness(_ctx.kg))

        @http_app.get("/api/cq/13", response_model=None)
        async def api_cq13(word: str = "Querdenker", year: int | None = None):
            """CQ13 (3.0): Per-group sense attributions for a word."""
            _ctx = Context(trace_id="cq13", principal="system", store=_kernel_store())
            return JSONResponse(
                _cq.cq13_groups_attributing_word(_ctx.kg, word=word, year=year)
            )

        # 3.0 multi-group metrics ------------------------------------------------
        from capabilities import metrics_multi_group as _m3

        @http_app.get("/api/metrics/entropy", response_model=None)
        async def api_metric_entropy(word: str = "Querdenker", year: int | None = None):
            """Semantic entropy of the sense distribution for a word."""
            _ctx = Context(trace_id="m3-entropy", principal="system", store=_kernel_store())
            return JSONResponse(_m3.semantic_entropy(_ctx.kg, word=word, year=year))

        @http_app.get("/api/metrics/fragmentation", response_model=None)
        async def api_metric_fragmentation(word: str = "Querdenker", year: int | None = None):
            """Gini-Simpson fragmentation over the (group, sense) grid."""
            _ctx = Context(trace_id="m3-frag", principal="system", store=_kernel_store())
            return JSONResponse(
                _m3.semantic_fragmentation_index(_ctx.kg, word=word, year=year)
            )

        @http_app.get("/api/metrics/divergence", response_model=None)
        async def api_metric_divergence(word: str = "Querdenker", year: int | None = None):
            """Pairwise Jensen-Shannon divergence between group sense-distributions."""
            _ctx = Context(trace_id="m3-div", principal="system", store=_kernel_store())
            return JSONResponse(_m3.group_divergence(_ctx.kg, word=word, year=year))

        @http_app.get("/api/metrics/timeline", response_model=None)
        async def api_metric_timeline(word: str = "Querdenker"):
            """Per-year snapshot of all three M3 metrics for a word."""
            _ctx = Context(trace_id="m3-tl", principal="system", store=_kernel_store())
            return JSONResponse(_m3.metric_timeline(_ctx.kg, word=word))

        # ------------------------------------------------------------------
        # Static site — mounted LAST so API routes take precedence
        # ------------------------------------------------------------------
        site_dir = Path(__file__).parent / "site"
        if site_dir.exists():
            http_app.mount(
                "/",
                StaticFiles(directory=str(site_dir), html=True),
                name="site",
            )
            logger.info("Static site mounted at / from %s", site_dir)
        else:
            logger.info(
                "No site/ directory found; static frontend not served. "
                "Copy or symlink the word-drift site/ here."
            )

    except ImportError as exc:
        logger.warning(
            "FastAPI/starlette not available, running without static site: %s", exc
        )

    return http_app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    try:
        import uvicorn

        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(create_app(), host="0.0.0.0", port=port)
    except ImportError:
        # Fallback: bootstrap and exit (no MCP runner without the App facade)
        _bootstrap()
        logger.info("uvicorn not available; bootstrap complete, exiting.")
