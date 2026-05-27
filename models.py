"""Trails model definitions for the word-drift lexical-change ontology.

Each class is registered as a Trails @node_type (the ORM layer) and
additionally annotated with a @shape (the SHACL layer) so that the
framework can validate instances on write and export constraints as
SHACL Turtle.

Namespaces
----------
drift   https://w3id.org/word-drift/ontology#
ontolex http://www.w3.org/ns/lemon/ontolex#
skos    http://www.w3.org/2004/02/skos/core#
rdfs    http://www.w3.org/2000/01/rdf-schema#
dct     http://purl.org/dc/terms/
time    http://www.w3.org/2006/time#
"""
from __future__ import annotations

import sys
import os

# Allow running from the project root without installing the package.
# Point TRAILS_SRC at a local framework.trails checkout (python/src) if Trails
# is not pip-installed; defaults to a sibling ../framework.trails checkout.
_TRAILS_SRC = os.environ.get(
    "TRAILS_SRC",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "framework.trails", "python", "src"),
)
if os.path.isdir(_TRAILS_SRC) and _TRAILS_SRC not in sys.path:
    sys.path.insert(0, _TRAILS_SRC)

from trails import node_type, shape, predicate, Model  # noqa: E402

# ---------------------------------------------------------------------------
# Namespace constants (used as prefix strings in predicate IRIs)
# ---------------------------------------------------------------------------

_DRIFT = "https://w3id.org/word-drift/ontology#"
_ONTOLEX = "http://www.w3.org/ns/lemon/ontolex#"
_SKOS = "http://www.w3.org/2004/02/skos/core#"
_RDFS = "http://www.w3.org/2000/01/rdf-schema#"
_DCT = "http://purl.org/dc/terms/"
_TIME = "http://www.w3.org/2006/time#"
_XSD = "http://www.w3.org/2001/XMLSchema#"
_OWL = "http://www.w3.org/2002/07/owl#"


# ---------------------------------------------------------------------------
# drift:Word
# A lexical entry under study (subClassOf ontolex:LexicalEntry).
# ---------------------------------------------------------------------------

@node_type(
    "Word",
    fields={
        "written_form": str,
        "language": str | None,
    },
    extends=[f"{_ONTOLEX}LexicalEntry"],
)
class Word:
    """A lexical entry whose meaning is being studied over time.

    ``written_form`` is the orthographic surface form (e.g. "Querdenker").
    ``language`` is a BCP-47 language tag (e.g. "de", "en"), optional.
    """


@shape(iri=f"{_DRIFT}WordShape")
class WordShape:
    """SHACL shape for drift:Word.

    Enforces that every Word carries exactly one writtenForm string.
    Language is optional (may be absent for reconstructed proto-forms).
    """

    written_form: str = predicate(
        f"{_DRIFT}writtenForm",
        required=True,
        many=False,
        min_length=1,
    )
    language: str | None = predicate(
        f"{_DRIFT}language",
        required=False,
        many=False,
    )


# ---------------------------------------------------------------------------
# drift:Sense
# A distinguishable meaning of a Word (subClassOf ontolex:LexicalSense).
# ---------------------------------------------------------------------------

@node_type(
    "Sense",
    fields={
        "gloss_en": str | None,
        "connotation": str | None,
        "connotation_id": str | None,
        "first_attested": int | None,
        "attested_interval_start": int | None,
        "attested_interval_end": int | None,
    },
    extends=[f"{_ONTOLEX}LexicalSense"],
)
class Sense:
    """A distinguishable meaning of a word; the unit that drifts.

    ``gloss_en`` is the English human-readable definition.
    ``connotation`` is the prefLabel of the connotation concept
        (positive / neutral / negative).
    ``connotation_id`` is the full IRI of the connotation concept.
    ``first_attested`` is the earliest year in which the sense is
        documented.
    ``attested_interval_start`` / ``attested_interval_end`` are the
        begin/end years of the attested interval when a span is known.
    """


@shape(iri=f"{_DRIFT}SenseShape")
class SenseShape:
    """SHACL shape for drift:Sense.

    All fields are optional at the SHACL level; a minimal sense carries
    at least a gloss, but benchmark/detection data may have none.
    """

    gloss_en: str | None = predicate(
        f"{_DRIFT}gloss",
        required=False,
        many=False,
    )
    connotation: str | None = predicate(
        f"{_DRIFT}connotation",
        required=False,
        many=False,
    )
    first_attested: int | None = predicate(
        f"{_DRIFT}firstAttested",
        required=False,
        many=False,
        min_value=1000,
        max_value=2100,
    )


# ---------------------------------------------------------------------------
# drift:DriftEvent
# A reified semantic-change episode affecting one word.
# ---------------------------------------------------------------------------

@node_type(
    "DriftEvent",
    fields={
        "affects_word": str,
        "sense_from_id": str | None,
        "sense_to_id": str | None,
        "drift_type_label": str | None,
        "drift_type_ids": list[str],
        "year": int | None,
        "year_end": int | None,
        "confidence": float | None,
        "trigger_ids": list[str],
    },
)
class DriftEvent:
    """A reified semantic-change episode.

    ``affects_word`` is the IRI of the word whose meaning shifted.
    ``sense_from_id`` / ``sense_to_id`` are IRIs of the pre/post senses.
    ``drift_type_label`` is a comma-joined human-readable label for the
        drift type(s) from drift:DriftTypeScheme.
    ``drift_type_ids`` are the full IRIs of all drift-type concepts.
    ``year`` / ``year_end`` are the approximate year span of the shift.
    ``confidence`` is from a CausalHypothesis (0.0–1.0), if present.
    ``trigger_ids`` are the IRIs of associated TriggerEvent nodes
        (reached via drift:CausalHypothesis).
    """


@shape(iri=f"{_DRIFT}DriftEventShape")
class DriftEventShape:
    """SHACL shape for drift:DriftEvent.

    ``affects_word`` is the only mandatory field; every other field
    is evidence-dependent and may be absent for detection-grade data.
    """

    affects_word: str = predicate(
        f"{_DRIFT}affectsWord",
        required=True,
        many=False,
    )
    year: int | None = predicate(
        f"{_DRIFT}driftYear",
        required=False,
        many=False,
        min_value=1000,
        max_value=2100,
    )
    confidence: float | None = predicate(
        f"{_DRIFT}confidence",
        required=False,
        many=False,
        min_value=0.0,
        max_value=1.0,
    )


# ---------------------------------------------------------------------------
# drift:TriggerEvent
# A datable real-world event proposed as the cause of a semantic shift.
# ---------------------------------------------------------------------------

@node_type(
    "TriggerEvent",
    fields={
        "label": str,
        "event_date": int | None,
        "category": str | None,
        "wikidata_same_as": str | None,
        "description": str | None,
    },
    extends=[f"http://www.w3.org/ns/prov#Activity"],
)
class TriggerEvent:
    """A real-world event linked to one or more drift events.

    ``label`` is the English human-readable label.
    ``event_date`` is the onset year (coarse anchor).
    ``category`` is the prefLabel of the trigger-category concept
        (political / pandemic / technological / cultural / media /
        commercial).
    ``wikidata_same_as`` is the Wikidata Q-IRI, if known.
    ``description`` is a longer DCT description, optional.
    """


@shape(iri=f"{_DRIFT}TriggerEventShape")
class TriggerEventShape:
    """SHACL shape for drift:TriggerEvent.

    Requires a human-readable label; all other fields are optional.
    """

    label: str = predicate(
        f"{_RDFS}label",
        required=True,
        many=False,
        min_length=1,
    )
    event_date: int | None = predicate(
        f"{_DRIFT}eventDate",
        required=False,
        many=False,
        min_value=1000,
        max_value=2100,
    )
    category: str | None = predicate(
        f"{_DRIFT}triggerCategory",
        required=False,
        many=False,
    )


# ---------------------------------------------------------------------------
# drift:CausalHypothesis
# An evidence-bearing, confidence-graded claim linking a DriftEvent
# to a TriggerEvent (ADR-0004 — causation is never asserted directly).
# ---------------------------------------------------------------------------

@node_type(
    "CausalHypothesis",
    fields={
        "about_drift": str,
        "proposed_trigger": str,
        "evidence_types": list[str],
        "confidence": float | None,
    },
    extends=[f"http://www.w3.org/ns/prov#Entity"],
)
class CausalHypothesis:
    """An evidenced causal claim (ADR-0004).

    ``about_drift`` is the IRI of the DriftEvent this hypothesis explains.
    ``proposed_trigger`` is the IRI of the proposed TriggerEvent.
    ``evidence_types`` are IRIs of drift:EvidenceTypeScheme concepts.
    ``confidence`` is a graded value in [0.0, 1.0].
    """


@shape(iri=f"{_DRIFT}CausalHypothesisShape")
class CausalHypothesisShape:
    """SHACL shape for drift:CausalHypothesis.

    Both aboutDrift and proposedTrigger are mandatory (functional in OWL).
    """

    about_drift: str = predicate(
        f"{_DRIFT}aboutDrift",
        required=True,
        many=False,
    )
    proposed_trigger: str = predicate(
        f"{_DRIFT}proposedTrigger",
        required=True,
        many=False,
    )
    confidence: float | None = predicate(
        f"{_DRIFT}confidence",
        required=False,
        many=False,
        min_value=0.0,
        max_value=1.0,
    )


# ---------------------------------------------------------------------------
# drift:FrequencyObservation
# A single (year, value) corpus-frequency measurement for a word/sense.
# ---------------------------------------------------------------------------

@node_type(
    "FrequencyObservation",
    fields={
        "of_word": str,
        "observed_year": int,
        "relative_frequency": float,
    },
)
class FrequencyObservation:
    """A per-year corpus-frequency measurement.

    ``of_word`` is the IRI of the measured drift:Word.
    ``observed_year`` is the observation year (xsd:gYear integer).
    ``relative_frequency`` is the relative frequency (per-million tokens,
        or similar normalisation; the exact scale is corpus-specific).
    """


@shape(iri=f"{_DRIFT}FrequencyObservationShape")
class FrequencyObservationShape:
    """SHACL shape for drift:FrequencyObservation.

    All three fields are mandatory: a headless observation is useless.
    """

    of_word: str = predicate(
        f"{_DRIFT}ofWord",
        required=True,
        many=False,
    )
    observed_year: int = predicate(
        f"{_DRIFT}observedYear",
        required=True,
        many=False,
        min_value=1000,
        max_value=2100,
    )
    relative_frequency: float = predicate(
        f"{_DRIFT}relativeFrequency",
        required=True,
        many=False,
        min_value=0.0,
    )
