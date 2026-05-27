"""Provenance invariants (ADR 0004):
- Every drift:DriftEvent must have at least one drift:hasSource.
- Every drift:CausalHypothesis must have a proposed trigger, a typed evidence,
  a confidence in [0.0, 1.0], and at least one source. Causation lives ONLY on
  the hypothesis; there is no drift:triggeredBy shortcut.
"""
from __future__ import annotations

import rdflib
from rdflib.namespace import RDF

DRIFT = rdflib.Namespace("https://w3id.org/word-drift/ontology#")


def test_drift_events_have_source(full_graph: rdflib.Graph) -> None:
    """Every drift:DriftEvent must cite at least one drift:hasSource."""
    violations: list[str] = []
    for event in full_graph.subjects(RDF.type, DRIFT.DriftEvent):
        if not list(full_graph.objects(event, DRIFT.hasSource)):
            violations.append(f"  <{event}> has no drift:hasSource")

    assert not violations, "Missing source violations:\n" + "\n".join(violations)


def test_no_triggered_by_shortcut(full_graph: rdflib.Graph) -> None:
    """The drift:triggeredBy shortcut was removed in v0.3; causation must be
    expressed via drift:CausalHypothesis only."""
    leftover = list(full_graph.subjects(DRIFT.triggeredBy, None))
    assert not leftover, (
        "drift:triggeredBy is removed (ADR 0004); use drift:CausalHypothesis. "
        f"Found {len(leftover)} leftover use(s)."
    )


def test_causal_hypotheses_well_formed(full_graph: rdflib.Graph) -> None:
    """Every drift:CausalHypothesis must have aboutDrift, proposedTrigger, an
    evidenceType, at least one source, and a confidence in [0.0, 1.0]."""
    violations: list[str] = []
    for hyp in full_graph.subjects(RDF.type, DRIFT.CausalHypothesis):
        if not list(full_graph.objects(hyp, DRIFT.aboutDrift)):
            violations.append(f"  <{hyp}> missing drift:aboutDrift")
        if not list(full_graph.objects(hyp, DRIFT.proposedTrigger)):
            violations.append(f"  <{hyp}> missing drift:proposedTrigger")
        if not list(full_graph.objects(hyp, DRIFT.evidenceType)):
            violations.append(f"  <{hyp}> missing drift:evidenceType")
        if not list(full_graph.objects(hyp, DRIFT.hasSource)):
            violations.append(f"  <{hyp}> missing drift:hasSource")

        confidence_values = list(full_graph.objects(hyp, DRIFT.confidence))
        if not confidence_values:
            violations.append(f"  <{hyp}> missing drift:confidence")
        for conf in confidence_values:
            try:
                value = float(conf)
            except (ValueError, TypeError):
                violations.append(f"  <{hyp}> drift:confidence not numeric: {conf!r}")
                continue
            if not (0.0 <= value <= 1.0):
                violations.append(
                    f"  <{hyp}> drift:confidence {value} outside [0.0, 1.0]"
                )

    assert not violations, "Causal hypothesis violations:\n" + "\n".join(violations)
