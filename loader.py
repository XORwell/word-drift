"""Load word-drift TTL data into the Trails kernel store.

Usage
-----
    from loader import load_all_ttl

    load_all_ttl()   # populates the Trails singleton store (in-memory by default)

Loading order is intentional: ontology modules first (vocabulary and
RDFS/OWL axioms), then examples (hand-curated rich data), then the bulk
data/ tree (benchmark, frequency, alignment data).  Files within each
directory are loaded in sorted order to produce deterministic triples.

After calling :func:`load_all_ttl`, all Trails ``Context`` objects (created
via ``invoke()``) share the same kernel store, so ``ctx.kg.query(...)``
will see the loaded data immediately.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("word_drift.loader")

# Canonical path to the word-drift data tree.  The TTL sources
# (``ontology/``, ``examples/``, ``data/``) ship inside this repo, so the
# default root is the directory holding this module — which is also where
# the Docker image mounts them.  Override by passing ``data_root`` to
# :func:`load_all_ttl`.
_DEFAULT_DATA_ROOT = Path(__file__).resolve().parent


def load_all_ttl(
    store_path: str = ":memory:",
    *,
    data_root: Path | str | None = None,
) -> None:
    """Load all word-drift TTL files into the Trails kernel store.

    Data is loaded into the Trails singleton backend store returned by
    ``trails.sdk.raw_kernel_store()``.  Because all ``Context``
    objects share this singleton, any ``ctx.kg.query(...)`` call issued
    after this function returns will see the loaded triples.

    Parameters
    ----------
    store_path:
        Accepted for backwards compatibility but no longer used to
        create a separate Oxigraph store.  Persistence is controlled by
        the Trails configuration (``graph.mode`` / ``TRAILS_DATA_DIR``).
    data_root:
        Root of the word-drift source tree.  Defaults to
        ``/tmp/word-drift-orig`` (the location used during development).
        Pass the repo root of a different clone to load a different
        dataset.

    Notes
    -----
    * Files that fail to parse are skipped with a WARNING log line.
    * Duplicate triples are silently ignored by Oxigraph (set semantics).
    * The store is opened transactionally per file: a parse error on one
      file does not corrupt previously loaded data.
    """
    import rdflib  # deferred so the module is importable without it

    from trails.sdk import raw_kernel_store

    # The kernel-side store singleton.  ``update`` writes into the default
    # graph, which is what word-drift's queries read.  All ``Context``
    # objects wrap this same singleton, so the data becomes visible to
    # ``ctx.kg.query`` as soon as this returns.
    store = raw_kernel_store()

    root = Path(data_root) if data_root is not None else _DEFAULT_DATA_ROOT

    # Load order: ontology (vocab/labels) → examples → data.
    dirs = [
        root / "ontology",
        root / "examples",
        root / "data",
    ]

    total = 0
    failed = 0

    for directory in dirs:
        if not directory.exists():
            logger.debug("skipping missing directory: %s", directory)
            continue

        ttl_files = sorted(directory.rglob("*.ttl"))
        logger.debug("scanning %s: %d TTL file(s)", directory, len(ttl_files))

        for ttl in ttl_files:
            try:
                # Parse with rdflib, then insert the triples into the
                # default graph via SPARQL INSERT DATA.  N-Triples is a
                # valid triples block inside INSERT DATA and uses absolute
                # IRIs only, so no prefix declarations are needed.
                graph = rdflib.Graph()
                graph.parse(str(ttl), format="turtle")
                if len(graph) == 0:
                    logger.debug("empty graph, skipping %s", ttl.relative_to(root))
                    continue
                nt_data = graph.serialize(format="nt")
                store.update("INSERT DATA {\n" + nt_data + "\n}")
                logger.debug("loaded %s (%d triples)", ttl.relative_to(root), len(graph))
                total += 1
            except Exception as exc:
                logger.warning("failed to load %s: %s", ttl, exc)
                failed += 1

    logger.info(
        "loaded %d TTL file(s) into Trails kernel store (%d failed)", total, failed
    )
    if failed:
        logger.warning("%d TTL file(s) skipped due to parse errors", failed)


def triple_count() -> int:
    """Return the number of triples in the Trails kernel store (convenience helper for tests)."""
    from trails.sdk import raw_kernel_store

    store = raw_kernel_store()
    # The core store returns SELECT bindings as plain term strings:
    # ``[{"n": "123"}]``.
    result = store.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    for row in result:
        v = row.get("n")
        if v is not None:
            return int(v)
    return 0
