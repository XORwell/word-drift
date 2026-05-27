"""Session-scoped fixtures: load ontology, shapes, examples, and full combined graph."""
from __future__ import annotations

from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parent.parent


def _load_ttl_dir(directory: Path) -> rdflib.Graph:
    """Parse all *.ttl files in *directory* (non-recursive) into one graph."""
    g = rdflib.Graph()
    for f in sorted(directory.glob("*.ttl")):
        g.parse(f, format="turtle")
    return g


@pytest.fixture(scope="session")
def ontology_graph() -> rdflib.Graph:
    """Graph containing all ontology/*.ttl triples."""
    return _load_ttl_dir(ROOT / "ontology")


@pytest.fixture(scope="session")
def shapes_graph() -> rdflib.Graph:
    """Graph containing all shapes/*.ttl triples."""
    return _load_ttl_dir(ROOT / "shapes")


@pytest.fixture(scope="session")
def examples_graph() -> rdflib.Graph:
    """Graph containing all examples/*.ttl triples (may be empty if dir absent)."""
    examples_dir = ROOT / "examples"
    if not examples_dir.exists():
        return rdflib.Graph()
    return _load_ttl_dir(examples_dir)


@pytest.fixture(scope="session")
def full_graph(ontology_graph, examples_graph) -> rdflib.Graph:
    """Union of ontology and examples graphs. Used for SPARQL queries."""
    combined = rdflib.Graph()
    combined += ontology_graph
    combined += examples_graph
    return combined
