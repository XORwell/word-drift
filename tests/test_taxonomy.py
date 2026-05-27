"""Taxonomy integrity: validate that SKOS Concept references in examples resolve to the
declared ConceptSchemes in the ontology."""
from __future__ import annotations

import rdflib
from rdflib.namespace import RDF, SKOS

DRIFT = rdflib.Namespace("https://w3id.org/word-drift/ontology#")


def _concepts_in_scheme(graph: rdflib.Graph, scheme: rdflib.URIRef) -> set[rdflib.URIRef]:
    """Return all skos:Concept IRIs declared with skos:inScheme *scheme*."""
    return {
        s
        for s, _, _ in graph.triples((None, SKOS.inScheme, scheme))
    }


def test_drift_types_in_scheme(full_graph: rdflib.Graph) -> None:
    """Every drift:driftType value used in examples must be a member of drift:DriftTypeScheme."""
    drift_type_scheme = DRIFT.DriftTypeScheme
    valid_types = _concepts_in_scheme(full_graph, drift_type_scheme)

    violations: list[str] = []
    for event, _, dtype in full_graph.triples((None, DRIFT.driftType, None)):
        if dtype not in valid_types:
            violations.append(
                f"  drift event <{event}> uses driftType <{dtype}> "
                f"which is not in drift:DriftTypeScheme"
            )

    assert not violations, "driftType violations:\n" + "\n".join(violations)


def test_connotations_in_scheme(full_graph: rdflib.Graph) -> None:
    """Every drift:connotation value used in examples must be a member of drift:ConnotationScheme."""
    connotation_scheme = DRIFT.ConnotationScheme
    valid_connotations = _concepts_in_scheme(full_graph, connotation_scheme)

    violations: list[str] = []
    for sense, _, connotation in full_graph.triples((None, DRIFT.connotation, None)):
        if connotation not in valid_connotations:
            violations.append(
                f"  sense <{sense}> uses connotation <{connotation}> "
                f"which is not in drift:ConnotationScheme"
            )

    assert not violations, "connotation violations:\n" + "\n".join(violations)


def test_trigger_categories_in_scheme(full_graph: rdflib.Graph) -> None:
    """Every drift:triggerCategory value used in examples must be in drift:TriggerCategoryScheme."""
    trigger_scheme = DRIFT.TriggerCategoryScheme
    valid_categories = _concepts_in_scheme(full_graph, trigger_scheme)

    violations: list[str] = []
    for trigger, _, category in full_graph.triples((None, DRIFT.triggerCategory, None)):
        if category not in valid_categories:
            violations.append(
                f"  trigger <{trigger}> uses triggerCategory <{category}> "
                f"which is not in drift:TriggerCategoryScheme"
            )

    assert not violations, "triggerCategory violations:\n" + "\n".join(violations)
