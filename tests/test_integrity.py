"""Structural integrity checks:

1. No orphan senses: every drift:Sense must either be reachable via ontolex:sense
   from a drift:Word, OR be referenced as senseFrom/senseTo on a drift:DriftEvent.

2. Every drift:DriftEvent must have:
   - drift:affectsWord
   - drift:senseTo
   - drift:driftType
   - at least one time anchor (drift:driftYear OR drift:driftInterval)
"""
from __future__ import annotations

import rdflib
from rdflib.namespace import RDF

DRIFT = rdflib.Namespace("https://w3id.org/word-drift/ontology#")
ONTOLEX = rdflib.Namespace("http://www.w3.org/ns/lemon/ontolex#")


def test_no_orphan_senses(full_graph: rdflib.Graph) -> None:
    """Every drift:Sense must be reachable from a drift:Word or a drift:DriftEvent."""
    # Senses linked from a Word via ontolex:sense
    senses_via_word: set[rdflib.URIRef] = set(
        full_graph.objects(None, ONTOLEX.sense)
    )
    # Senses referenced by a DriftEvent (senseFrom or senseTo)
    senses_via_event: set[rdflib.URIRef] = set(
        full_graph.objects(None, DRIFT.senseFrom)
    ) | set(full_graph.objects(None, DRIFT.senseTo))

    reachable = senses_via_word | senses_via_event

    violations: list[str] = []
    for sense in full_graph.subjects(RDF.type, DRIFT.Sense):
        if sense not in reachable:
            violations.append(
                f"  <{sense}> is a drift:Sense but is not linked from any "
                "drift:Word (ontolex:sense) or drift:DriftEvent (senseFrom/senseTo)"
            )

    assert not violations, "Orphan sense violations:\n" + "\n".join(violations)


def test_drift_events_required_properties(full_graph: rdflib.Graph) -> None:
    """Every drift:DriftEvent must have affectsWord, senseTo, driftType, and a time anchor."""
    violations: list[str] = []
    for event in full_graph.subjects(RDF.type, DRIFT.DriftEvent):
        missing: list[str] = []

        if not list(full_graph.objects(event, DRIFT.affectsWord)):
            missing.append("drift:affectsWord")

        if not list(full_graph.objects(event, DRIFT.senseTo)):
            missing.append("drift:senseTo")

        if not list(full_graph.objects(event, DRIFT.driftType)):
            missing.append("drift:driftType")

        # At least one time anchor required.
        has_year = bool(list(full_graph.objects(event, DRIFT.driftYear)))
        has_interval = bool(list(full_graph.objects(event, DRIFT.driftInterval)))
        if not (has_year or has_interval):
            missing.append("drift:driftYear or drift:driftInterval (none present)")

        if missing:
            violations.append(
                f"  <{event}> is missing: {', '.join(missing)}"
            )

    assert not violations, "DriftEvent required-property violations:\n" + "\n".join(violations)
