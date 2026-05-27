"""SHACL validation: examples + ontology must conform to the shapes graph."""
from __future__ import annotations

import rdflib
import pytest
from pyshacl import validate as shacl_validate


def test_examples_conform_to_shapes(ontology_graph, shapes_graph, examples_graph) -> None:
    """All example instances must pass SHACL validation with RDFS inference enabled."""
    # Mirror exactly what validate.py does: data = examples + ontology.
    data = examples_graph + ontology_graph

    conforms, _, report_text = shacl_validate(
        data_graph=data,
        shacl_graph=shapes_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
        sparql_mode=False,
    )

    assert conforms, (
        "SHACL validation failed. Report:\n" + report_text
    )
