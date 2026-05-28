"""Word-Drift competency questions as Python functions.

Each function takes a Trails KG object (``ctx.kg``) and optional parameters and
returns a list of dicts. These are the 12 competency questions that define
the knowledge graph's scope and are used both as Trails @capability handlers
(in app.py) and as direct REST API endpoints (GET /api/cq/NN).

Query sources: /tmp/word-drift-orig/queries/competency/cq*.rq
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from trails.context import KG


# ---------------------------------------------------------------------------
# CQ01 — Which trigger event reframed the most words?
# ---------------------------------------------------------------------------

def cq01_most_reframed(kg: Any, *, limit: int = 10) -> list[dict[str, Any]]:
    """CQ01: Ranks trigger events by the number of distinct words reframed.

    Parameters
    ----------
    kg:
        Trails KG object (ctx.kg).
    limit:
        Maximum number of rows to return (default 10).

    Returns
    -------
    list of dicts with keys: triggerLabel, eventYear, wordCount, words
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?triggerLabel ?eventYear
       (COUNT(DISTINCT ?word) AS ?wordCount)
       (GROUP_CONCAT(DISTINCT ?writtenForm; SEPARATOR=", ") AS ?words)
WHERE {
  ?hyp a drift:CausalHypothesis ;
       drift:aboutDrift ?driftEvent ;
       drift:proposedTrigger ?trigger .
  ?driftEvent drift:affectsWord ?word .
  ?word drift:writtenForm ?writtenForm .
  OPTIONAL { ?trigger rdfs:label ?triggerLabel . FILTER(lang(?triggerLabel) = "en") }
  OPTIONAL { ?trigger drift:eventDate ?eventYear . }
}
GROUP BY ?trigger ?triggerLabel ?eventYear
ORDER BY DESC(?wordCount) ?eventYear
"""
    results = kg.query(sparql)
    return results[:limit]


# ---------------------------------------------------------------------------
# CQ02 — All causal hypotheses for a given word
# ---------------------------------------------------------------------------

def cq02_hypotheses_for_word(
    kg: Any, *, word: str = "Querdenker"
) -> list[dict[str, Any]]:
    """CQ02: All causal hypotheses for a given word, with evidence type and confidence.

    Parameters
    ----------
    kg:
        Trails KG object (ctx.kg).
    word:
        The written form of the word to query (default ``"Querdenker"``).

    Returns
    -------
    list of dicts with keys: word, trigger, evidence, confidence
    """
    sparql = f"""
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?word ?trigger ?evidence ?confidence WHERE {{
  ?h a drift:CausalHypothesis ;
     drift:aboutDrift ?e ;
     drift:proposedTrigger ?tr ;
     drift:evidenceType ?ev ;
     drift:confidence ?confidence .
  ?e drift:affectsWord ?w .
  ?w drift:writtenForm ?word .
  FILTER(STR(?word) = "{word}")
  ?tr rdfs:label ?trigger .
  FILTER(lang(?trigger) = "en")
  ?ev skos:prefLabel ?evidence .
  FILTER(lang(?evidence) = "en")
}}
ORDER BY DESC(?confidence) ?evidence
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ03 — Drift-type distribution by trigger category
# ---------------------------------------------------------------------------

def cq03_drifttype_by_trigger(kg: Any) -> list[dict[str, Any]]:
    """CQ03: Drift-type distribution by trigger category.

    Cross-tabulates the typed change (drift:driftType) against the category of
    the proposed trigger, counting the causal hypotheses that connect them.

    Returns
    -------
    list of dicts with keys: category, driftType, n
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>

SELECT ?category ?driftType (COUNT(*) AS ?n) WHERE {
  ?h a drift:CausalHypothesis ;
     drift:aboutDrift ?e ;
     drift:proposedTrigger ?tr .
  ?e drift:driftType ?t .
  ?t skos:prefLabel ?driftType .
  FILTER(lang(?driftType) = "en")
  ?tr drift:triggerCategory ?c .
  ?c skos:prefLabel ?category .
  FILTER(lang(?category) = "en")
}
GROUP BY ?category ?driftType
ORDER BY ?category DESC(?n)
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ04 — Same-direction drift across DE and EN
# ---------------------------------------------------------------------------

def cq04_cross_lingual_same_direction(kg: Any) -> list[dict[str, Any]]:
    """CQ04: Pairs words in different languages with the same drift type.

    Lexicographic guard on the word IRIs avoids reporting both (A,B) and (B,A).

    Returns
    -------
    list of dicts with keys: driftTypeLabel, word1, lang1, year1, word2, lang2, year2
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>

SELECT ?driftTypeLabel
       ?word1 ?lang1 ?year1
       ?word2 ?lang2 ?year2
WHERE {
  ?e1 a drift:DriftEvent ; drift:affectsWord ?w1 ; drift:driftType ?t .
  ?w1 drift:writtenForm ?word1 ; drift:language ?lang1 .
  OPTIONAL { ?e1 drift:driftYear ?year1 . }

  ?e2 a drift:DriftEvent ; drift:affectsWord ?w2 ; drift:driftType ?t .
  ?w2 drift:writtenForm ?word2 ; drift:language ?lang2 .
  OPTIONAL { ?e2 drift:driftYear ?year2 . }

  FILTER(?lang1 != ?lang2)
  FILTER(STR(?w1) < STR(?w2))

  OPTIONAL { ?t skos:prefLabel ?driftTypeLabel . FILTER(lang(?driftTypeLabel) = "en") }
}
ORDER BY ?driftTypeLabel ?lang1 ?word1
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ05 — Words whose connotation reversed
# ---------------------------------------------------------------------------

def cq05_connotation_reversed(kg: Any) -> list[dict[str, Any]]:
    """CQ05: Words whose connotation reversed (positive <-> negative).

    Captures both pejoration (positive -> negative) and amelioration /
    reappropriation (negative -> positive) at the valence level.

    Returns
    -------
    list of dicts with keys: word, fromConn, toConn, year
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>

SELECT ?word ?fromConn ?toConn ?year WHERE {
  ?e a drift:DriftEvent ;
     drift:affectsWord ?w ;
     drift:senseFrom ?sf ;
     drift:senseTo ?st .
  ?w drift:writtenForm ?word .
  ?sf drift:connotation ?cf .
  ?st drift:connotation ?ct .
  FILTER( (?cf = drift:Positive && ?ct = drift:Negative) ||
          (?cf = drift:Negative && ?ct = drift:Positive) )
  ?cf skos:prefLabel ?fromConn . FILTER(lang(?fromConn) = "en")
  ?ct skos:prefLabel ?toConn .   FILTER(lang(?toConn) = "en")
  OPTIONAL { ?e drift:driftYear ?year . }
}
ORDER BY ?year ?word
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ06 — Trigger events in a date range
# ---------------------------------------------------------------------------

def cq06_triggers_in_date_range(
    kg: Any, *, year_from: int = 1900, year_to: int = 1999
) -> list[dict[str, Any]]:
    """CQ06: All trigger events whose eventDate falls within [year_from, year_to].

    Uses ``xsd:integer(STR(?year))`` cast so the query runs on Oxigraph,
    rdflib, QLever, and Jena identically (direct gYear comparison silently
    returns no rows on rdflib).

    Parameters
    ----------
    kg:
        Trails KG object (ctx.kg).
    year_from:
        Start year, inclusive (default 1900).
    year_to:
        End year, inclusive (default 1999).

    Returns
    -------
    list of dicts with keys: triggerLabel, year, category, words
    """
    sparql = f"""
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>

SELECT ?triggerLabel ?year ?category (COUNT(DISTINCT ?word) AS ?words) WHERE {{
  ?tr a drift:TriggerEvent ;
      drift:eventDate ?year .
  BIND(xsd:integer(STR(?year)) AS ?y)
  FILTER(?y >= {year_from} && ?y <= {year_to})
  OPTIONAL {{ ?tr rdfs:label ?triggerLabel . FILTER(lang(?triggerLabel) = "en") }}
  OPTIONAL {{
    ?tr drift:triggerCategory ?c .
    ?c skos:prefLabel ?category .
    FILTER(lang(?category) = "en")
  }}
  OPTIONAL {{
    ?h drift:proposedTrigger ?tr ; drift:aboutDrift ?e .
    ?e drift:affectsWord ?word .
  }}
}}
GROUP BY ?tr ?triggerLabel ?year ?category
ORDER BY ?year ?triggerLabel
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ07 — Hypotheses resting ONLY on speculative evidence
# ---------------------------------------------------------------------------

def cq07_speculative_only(kg: Any) -> list[dict[str, Any]]:
    """CQ07: Hypotheses resting ONLY on speculative evidence.

    A quality probe: non-empty results flag curation debt, not a data error.
    The SHACL shape requires >=1 evidence type but does NOT require a
    non-speculative one, so this query may return rows even on a fully
    conformant graph.

    Returns
    -------
    list of dicts with keys: hypothesis, word, confidence
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>

SELECT ?hypothesis ?word ?confidence WHERE {
  ?h a drift:CausalHypothesis ;
     drift:aboutDrift ?e ;
     drift:confidence ?confidence .
  ?e drift:affectsWord ?w .
  ?w drift:writtenForm ?word .
  FILTER NOT EXISTS {
    ?h drift:evidenceType ?ev .
    FILTER(?ev != drift:Speculative)
  }
  BIND(STRAFTER(STR(?h), "resource/") AS ?hypothesis)
}
ORDER BY DESC(?confidence) ?word
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ08 — Strongest evidence tier backing each drift event
# ---------------------------------------------------------------------------

def cq08_strongest_evidence(kg: Any) -> list[dict[str, Any]]:
    """CQ08: Strongest evidence tier backing each drift event.

    Evidence ladder (lowest to highest):
      Speculative(1) < FrequencyCorrelation(2) < ChangeSignalAlignment(3)
      < LexicographicNote(4) < ScholarlyAttestation(5)

    Returns
    -------
    list of dicts with keys: word, strongestTier
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>

SELECT ?word (MAX(?rank) AS ?strongestTier) WHERE {
  ?h a drift:CausalHypothesis ;
     drift:aboutDrift ?e ;
     drift:evidenceType ?ev .
  ?e drift:affectsWord ?w .
  ?w drift:writtenForm ?word .
  BIND(
    IF(?ev = drift:ScholarlyAttestation, 5,
    IF(?ev = drift:LexicographicNote,    4,
    IF(?ev = drift:ChangeSignalAlignment, 3,
    IF(?ev = drift:FrequencyCorrelation, 2,
    IF(?ev = drift:Speculative,          1, 0))))) AS ?rank)
}
GROUP BY ?word
ORDER BY DESC(?strongestTier) ?word
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ09 — Drift events with competing causal hypotheses
# ---------------------------------------------------------------------------

def cq09_competing_hypotheses(kg: Any) -> list[dict[str, Any]]:
    """CQ09: Drift events with competing causal hypotheses (more than one trigger).

    Returns
    -------
    list of dicts with keys: word, nTriggers, minConf, maxConf
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>

SELECT ?word
       (COUNT(DISTINCT ?trigger) AS ?nTriggers)
       (MIN(?conf) AS ?minConf)
       (MAX(?conf) AS ?maxConf)
WHERE {
  ?h a drift:CausalHypothesis ;
     drift:aboutDrift ?e ;
     drift:proposedTrigger ?trigger ;
     drift:confidence ?conf .
  ?e drift:affectsWord ?w .
  ?w drift:writtenForm ?word .
}
GROUP BY ?e ?word
HAVING (COUNT(DISTINCT ?trigger) > 1)
ORDER BY DESC(?nTriggers) ?word
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ10 — Per-word sense timeline with connotation
# ---------------------------------------------------------------------------

def cq10_sense_timeline(kg: Any) -> list[dict[str, Any]]:
    """CQ10: Per-word sense timeline with connotation, ordered by first attestation.

    Drives the timeline view: each sense of each word, its gloss, its valence,
    and the year it is first attested.

    Returns
    -------
    list of dicts with keys: word, year, connotation, gloss
    """
    sparql = """
PREFIX drift:   <https://w3id.org/word-drift/ontology#>
PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>

SELECT ?word ?year ?connotation ?gloss WHERE {
  ?w a drift:Word ;
     drift:writtenForm ?word ;
     ontolex:sense ?sense .
  ?sense drift:gloss ?gloss ;
         drift:connotation ?c .
  OPTIONAL { ?sense drift:firstAttested ?year . }
  ?c skos:prefLabel ?connotation . FILTER(lang(?connotation) = "en")
  FILTER(lang(?gloss) = "en")
}
ORDER BY ?word ?year
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ11 — Reclaimed (reappropriated) words and their triggers
# ---------------------------------------------------------------------------

def cq11_reappropriation_words(kg: Any) -> list[dict[str, Any]]:
    """CQ11: Words whose drift is typed drift:Reappropriation.

    A formerly derogatory term reclaimed by an in-group. Distinct from plain
    amelioration in the taxonomy.

    Returns
    -------
    list of dicts with keys: word, year, triggerLabel, confidence
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?word ?year ?triggerLabel ?confidence WHERE {
  ?e a drift:DriftEvent ;
     drift:affectsWord ?w ;
     drift:driftType drift:Reappropriation .
  ?w drift:writtenForm ?word .
  OPTIONAL { ?e drift:driftYear ?year . }
  OPTIONAL {
    ?h drift:aboutDrift ?e ;
       drift:proposedTrigger ?tr ;
       drift:confidence ?confidence .
    ?tr rdfs:label ?triggerLabel . FILTER(lang(?triggerLabel) = "en")
  }
}
ORDER BY ?year ?word
"""
    return kg.query(sparql)


# ---------------------------------------------------------------------------
# CQ12 — Provenance completeness (drift events with sources)
# ---------------------------------------------------------------------------

def cq12_provenance_completeness(kg: Any) -> list[dict[str, Any]]:
    """CQ12: Drift events provenanced to at least one source.

    Every drift event must cite a source (SHACL drift:hasSource minCount 1).
    Distinct source count per drift event lets a reviewer spot single-sourced
    vs corroborated claims.

    Returns
    -------
    list of dicts with keys: word, nSources, sources
    """
    sparql = """
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX dct:   <http://purl.org/dc/terms/>

SELECT ?word
       (COUNT(DISTINCT ?src) AS ?nSources)
       (GROUP_CONCAT(DISTINCT ?title; SEPARATOR=" | ") AS ?sources)
WHERE {
  ?e a drift:DriftEvent ;
     drift:affectsWord ?w ;
     drift:hasSource ?src .
  ?w drift:writtenForm ?word .
  OPTIONAL { ?src dct:title ?title . }
}
GROUP BY ?e ?word
ORDER BY DESC(?nSources) ?word
"""
    return kg.query(sparql)


# ===========================================================================
# 3.0 — Multi-group competency questions (CQ13+)
# ===========================================================================


# ---------------------------------------------------------------------------
# CQ13 — Which groups currently attribute sense X to word W?
# ---------------------------------------------------------------------------

def cq13_groups_attributing_word(
    kg: Any,
    *,
    word: str = "Querdenker",
    year: int | None = None,
) -> list[dict[str, Any]]:
    """CQ13 (3.0): Per-group sense attributions for a given word.

    Returns one row per (group, sense) pair with the attribution weight
    summed across the matching time window. Implements ADR-0002: the
    "dominant meaning" is not stored; the caller aggregates from rows.

    Parameters
    ----------
    kg:
        Trails KG object (ctx.kg).
    word:
        The written form of the target Word (case-sensitive).
    year:
        Optional snapshot year. If given, restricts attributions to
        ``atYear == year``; otherwise returns the full history.

    Returns
    -------
    list of dicts with keys:
        word, groupLabel, groupKind, senseGloss, atYear, weightSum, nAttribs
    """
    # gYear is a typed literal; compare on the lexical form so the query is
    # agnostic to xsd:gYear vs xsd:integer encoding in the source data.
    year_filter = f'FILTER(STR(?atYear) = "{int(year)}")' if year is not None else ""
    sparql = f"""
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?word ?groupLabel ?groupKindLabel ?senseGloss ?atYear
       (SUM(COALESCE(?w, 1.0)) AS ?weightSum)
       (COUNT(?ma) AS ?nAttribs)
WHERE {{
  ?ma a drift:MeaningAttribution ;
      drift:attributesWord ?wordIri ;
      drift:attributesSense ?senseIri ;
      drift:byGroup ?groupIri .
  ?wordIri drift:writtenForm ?word .
  FILTER(STR(?word) = "{word}")
  ?groupIri rdfs:label ?groupLabel .
  OPTIONAL {{
    ?groupIri drift:groupKind ?gk .
    ?gk <http://www.w3.org/2004/02/skos/core#prefLabel> ?groupKindLabel .
  }}
  OPTIONAL {{
    ?senseIri drift:gloss ?senseGloss .
    FILTER(LANG(?senseGloss) = "en" || LANG(?senseGloss) = "")
  }}
  OPTIONAL {{ ?ma drift:atYear ?atYear . }}
  OPTIONAL {{ ?ma drift:attributionWeight ?w . }}
  {year_filter}
}}
GROUP BY ?word ?groupLabel ?groupKindLabel ?senseGloss ?atYear
ORDER BY ?atYear ?groupLabel
"""
    return kg.query(sparql)
