"""SPARQL queries: every .rq file in queries/ must parse and return >= 1 row."""
from __future__ import annotations

from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parent.parent

# Non-recursive glob on queries/ only -- excludes queries/federated/ (SERVICE queries
# that cannot run offline), matching the behaviour of validate.py's glob("*.rq").
_QUERY_FILES = sorted((ROOT / "queries").glob("*.rq"))


@pytest.mark.parametrize(
    "rq_file",
    _QUERY_FILES,
    ids=lambda p: p.name,
)
def test_query_parses_and_returns_results(rq_file: Path, full_graph: rdflib.Graph) -> None:
    """Each SPARQL query must parse without error and return at least one result row."""
    sparql_text = rq_file.read_text(encoding="utf-8")

    # Execute against the combined ontology+examples graph.
    result = full_graph.query(sparql_text)
    rows = list(result)

    assert len(rows) >= 1, (
        f"Query {rq_file.name} returned 0 rows against the full graph. "
        "Either the query is broken or the examples do not satisfy its pattern."
    )
