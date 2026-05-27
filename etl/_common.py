"""
_common.py -- Shared helpers for WORD-DRIFT ETL adapters.

Provides:
  - Namespace bindings for the WORD-DRIFT vocabulary.
  - make_graph()         : rdflib.ConjunctiveGraph with prefixes bound.
  - slugify(text)        : lowercase IRI-safe slug.
  - write_turtle(g, path): serialise to Turtle at path.
  - validate_against_shapes(g): run pyshacl over ../shapes/, return (conforms, report).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Tuple

import rdflib
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

# ---------------------------------------------------------------------------
# Canonical namespace objects
# ---------------------------------------------------------------------------

DRIFT   = Namespace("https://w3id.org/word-drift/ontology#")
WDR     = Namespace("https://w3id.org/word-drift/resource/")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
TIME    = Namespace("http://www.w3.org/2006/time#")
PROV    = Namespace("http://www.w3.org/ns/prov#")
DCT     = Namespace("http://purl.org/dc/terms/")
WD      = Namespace("http://www.wikidata.org/entity/")

# Re-export the standard ones so adapters only import from _common.
__all__ = [
    "DRIFT", "WDR", "ONTOLEX", "TIME", "PROV", "DCT", "WD",
    "OWL", "RDF", "RDFS", "SKOS", "XSD",
    "make_graph", "slugify", "write_turtle", "validate_against_shapes",
]

# Shapes directory (relative to this file: etl/../shapes)
_SHAPES_DIR = Path(__file__).resolve().parent.parent / "shapes"
# Ontology directory (etl/../ontology) -- needed as inference base for SHACL class checks
_ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "ontology"


def make_graph() -> Graph:
    """Return a new rdflib.Graph with all project prefixes bound."""
    g = Graph()
    g.bind("drift",   DRIFT)
    g.bind("wdr",     WDR)
    g.bind("ontolex", ONTOLEX)
    g.bind("time",    TIME)
    g.bind("prov",    PROV)
    g.bind("dct",     DCT)
    g.bind("skos",    SKOS)
    g.bind("owl",     OWL)
    g.bind("rdfs",    RDFS)
    g.bind("xsd",     XSD)
    g.bind("wd",      WD)
    return g


def slugify(text: str) -> str:
    """
    Convert arbitrary text to a lowercase, hyphenated, IRI-safe slug.

    Example: "Querdenker"  -> "querdenker"
             "Corona Virus" -> "corona-virus"
    """
    # Normalise unicode (NFD), then drop combining characters.
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase, replace whitespace / special chars with hyphens.
    slug = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def write_turtle(g: Graph, path: str | Path) -> None:
    """Serialise *g* to Turtle at *path* (creates parent dirs if needed)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(p), format="turtle")
    print(f"  wrote {p}  ({len(g)} triples)")


def validate_against_shapes(g: Graph) -> Tuple[bool, str]:
    """
    Run pyshacl against every .ttl file in ../shapes/.

    Returns (conforms: bool, report_text: str).
    Requires pyshacl >= 0.25.
    """
    try:
        from pyshacl import validate as shacl_validate
    except ImportError as exc:
        raise RuntimeError("pyshacl not installed (pip install pyshacl)") from exc

    # Load all shape files into one graph.
    shapes_g = Graph()
    for ttl in sorted(_SHAPES_DIR.glob("*.ttl")):
        shapes_g.parse(ttl, format="turtle")

    # Load ontology as the inference base so that class declarations like
    # drift:Neutral a skos:Concept are visible during sh:class checks.
    ont_g = Graph()
    for ttl in sorted(_ONTOLOGY_DIR.glob("*.ttl")):
        ont_g.parse(ttl, format="turtle")

    conforms, _, report_text = shacl_validate(
        data_graph=g,
        shacl_graph=shapes_g,
        ont_graph=ont_g,
        inference="rdfs",
        abort_on_first=False,
        advanced=True,
        debug=False,
    )
    return conforms, report_text
