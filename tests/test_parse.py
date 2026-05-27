"""Verify every Turtle file in ontology/, shapes/, and examples/ parses without error."""
from __future__ import annotations

from pathlib import Path

import pytest
import rdflib

ROOT = Path(__file__).resolve().parent.parent

# Collect all .ttl files across the three source directories.
_TTL_FILES = sorted(
    list((ROOT / "ontology").glob("*.ttl"))
    + list((ROOT / "shapes").glob("*.ttl"))
    + (list((ROOT / "examples").glob("*.ttl")) if (ROOT / "examples").exists() else [])
)


@pytest.mark.parametrize("ttl_file", _TTL_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_turtle_file_parses(ttl_file: Path) -> None:
    """Each .ttl file must parse into a non-empty rdflib Graph without raising."""
    g = rdflib.Graph()
    # parse() raises on syntax errors; this is what we want to catch.
    g.parse(ttl_file, format="turtle")
    # A valid ontology/shape/example file should contribute at least one triple.
    assert len(g) > 0, f"{ttl_file.relative_to(ROOT)} produced zero triples"
