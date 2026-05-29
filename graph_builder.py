"""Build the word-drift graph-core.json / graph-detail.json from a Trails KG.

This module is a SPARQL-native rewrite of the original ``viz/export.py``.
It produces the same JSON contract (see ``site/DATA-CONTRACT.md``) but
queries a Trails ``KG`` object (``ctx.kg``) instead of a raw Oxigraph store.

Usage
-----
    from graph_builder import build_graph_document, split_document

    doc   = build_graph_document(ctx.kg)
    core, detail = split_document(doc)

Contract
--------
See /tmp/word-drift-orig/site/DATA-CONTRACT.md and the docstring of
:func:`build_graph_document` for the full JSON schema.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from trails.sdk import KG

logger = logging.getLogger("word_drift.graph_builder")

# ---------------------------------------------------------------------------
# SPARQL prefix block — prepended to every query
# ---------------------------------------------------------------------------

PREFIXES = """
PREFIX drift:   <https://w3id.org/word-drift/ontology#>
PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX dct:     <http://purl.org/dc/terms/>
PREFIX time:    <http://www.w3.org/2006/time#>
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
"""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _val(binding: Any) -> str | None:
    """Return the string value from a ``kg.query()`` result binding.

    ``KG.query()`` already returns plain strings (or ``None``) for each
    variable — no ``.value`` unwrapping is needed.

    Returns
    -------
    str | None
        The plain string as returned by ``KG.query()``, or ``None`` when
        the binding is unbound (OPTIONAL match failed).
    """
    if binding is None:
        return None
    return binding


def _int_val(binding: Any) -> int | None:
    """Parse a binding to int (gYear literals strip any leading '+')."""
    s = _val(binding)
    if s is None:
        return None
    try:
        return int(s.lstrip("+"))
    except (ValueError, TypeError):
        return None


def _float_val(binding: Any) -> float | None:
    """Parse a binding to float."""
    s = _val(binding)
    if s is None:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None




# ---------------------------------------------------------------------------
# Source / quality derivation (mirrors original export.py logic)
# ---------------------------------------------------------------------------


def derive_source(word_uri: str) -> str:
    """Map a word IRI to a human-readable source label."""
    local = word_uri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
    if "-gfds-" in local:
        return "GfdS"
    if "-freq-" in local:
        return "Frequency"
    if "-owid-" in local:
        return "OWID"
    if "-dwug-" in local:
        return "DWUG"
    if "-semeval-" in local:
        return "SemEval"
    return "Curated"


def derive_quality(source: str) -> str:
    """Map a source label to a quality tier."""
    if source in ("GfdS", "OWID", "Curated"):
        return "high"
    if source in ("DWUG", "SemEval"):
        return "benchmark"
    # Frequency or unknown
    return "detected"


# ---------------------------------------------------------------------------
# Query: triggers
# ---------------------------------------------------------------------------


def build_triggers(kg: "KG") -> list[dict]:
    """Return all drift:TriggerEvent nodes as dicts.

    Returns
    -------
    list[dict]
        Each dict has keys: ``id``, ``label``, ``date``, ``category``,
        ``wikidataSameAs``, ``description``.
    """
    rows = kg.query(PREFIXES + """
        SELECT DISTINCT ?te ?labelEn ?labelAny ?catLabel ?date ?sameAs ?desc
        WHERE {
          ?te a drift:TriggerEvent .
          OPTIONAL { ?te rdfs:label ?labelEn   FILTER (lang(?labelEn) = "en") }
          OPTIONAL { ?te rdfs:label ?labelAny }
          OPTIONAL {
            ?te drift:triggerCategory ?cat .
            OPTIONAL { ?cat skos:prefLabel ?catLabel FILTER (lang(?catLabel) = "en") }
            OPTIONAL { ?cat skos:prefLabel ?catLabel }
          }
          OPTIONAL { ?te drift:eventDate ?date }
          OPTIONAL { ?te owl:sameAs ?sameAs }
          OPTIONAL { ?te dct:description ?desc }
        }
        ORDER BY ?te
        """)

    # Collapse multiple rows per trigger (multiple sameAs / labels).
    trigger_map: dict[str, dict] = {}
    for row in rows:
        te_id = _val(row.get("te"))
        if not te_id:
            continue
        if te_id not in trigger_map:
            label = (
                _val(row.get("labelEn"))
                or _val(row.get("labelAny"))
                or te_id.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            )
            trigger_map[te_id] = {
                "id": te_id,
                "label": label,
                "date": _int_val(row.get("date")),
                "category": _val(row.get("catLabel")),
                "wikidataSameAs": _val(row.get("sameAs")),
                "description": _val(row.get("desc")),
            }
        else:
            # Merge: prefer English label; collect first sameAs.
            existing = trigger_map[te_id]
            if existing["wikidataSameAs"] is None:
                same = _val(row.get("sameAs"))
                if same:
                    existing["wikidataSameAs"] = same
            if existing["category"] is None:
                cat = _val(row.get("catLabel"))
                if cat:
                    existing["category"] = cat

    return list(trigger_map.values())


# ---------------------------------------------------------------------------
# Query: drift events + causal hypotheses
# ---------------------------------------------------------------------------


def build_drift_events(kg: "KG") -> list[dict]:
    """Return all drift:DriftEvent nodes as dicts.

    Trigger links are resolved via the drift:CausalHypothesis reification
    (ADR-0004) with a legacy fallback to direct drift:triggeredBy.

    Returns
    -------
    list[dict]
        Each dict has keys: ``id``, ``wordId``, ``senseFromId``,
        ``senseToId``, ``driftTypeLabel``, ``driftTypeIds``, ``year``,
        ``yearEnd``, ``confidence``, ``triggerIds``.
    """
    # Base drift event attributes.
    base_rows = kg.query(PREFIXES + """
        SELECT ?de ?word ?senseFrom ?senseTo ?year ?confidence
        WHERE {
          ?de a drift:DriftEvent ;
              drift:affectsWord ?word .
          OPTIONAL { ?de drift:senseFrom ?senseFrom }
          OPTIONAL { ?de drift:senseTo ?senseTo }
          OPTIONAL { ?de drift:driftYear ?year }
          OPTIONAL { ?de drift:confidence ?confidence }
        }
        ORDER BY ?de
        """)

    # Drift-interval fallback (begin/end year when driftYear is absent).
    interval_rows = kg.query(PREFIXES + """
        SELECT ?de ?beginYear ?endYear
        WHERE {
          ?de a drift:DriftEvent .
          ?de drift:driftInterval ?interval .
          OPTIONAL {
            ?interval time:hasBeginning ?begin .
            ?begin time:inXSDgYear ?beginYear .
          }
          OPTIONAL {
            ?interval time:hasEnd ?end .
            ?end time:inXSDgYear ?endYear .
          }
        }
        """)
    interval_map: dict[str, tuple[int | None, int | None]] = {}
    for r in interval_rows:
        de_id = _val(r.get("de"))
        if de_id:
            interval_map[de_id] = (
                _int_val(r.get("beginYear")),
                _int_val(r.get("endYear")),
            )

    # Drift types per event.
    dtype_rows = kg.query(PREFIXES + """
        SELECT ?de ?dt ?dtLabel
        WHERE {
          ?de a drift:DriftEvent ;
              drift:driftType ?dt .
          OPTIONAL { ?dt skos:prefLabel ?dtLabel FILTER (lang(?dtLabel) = "en") }
          OPTIONAL { ?dt skos:prefLabel ?dtLabel }
        }
        ORDER BY ?de ?dt
        """)
    dtype_map: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for r in dtype_rows:
        de_id = _val(r.get("de"))
        dt_id = _val(r.get("dt"))
        dt_label = _val(r.get("dtLabel"))
        if de_id and dt_id:
            dtype_map[de_id].append((dt_id, dt_label))

    # Trigger links via CausalHypothesis (canonical path, ADR-0004).
    hyp_rows = kg.query(PREFIXES + """
        SELECT ?de ?trigger ?conf ?evType ?evLabel
        WHERE {
          ?hyp a drift:CausalHypothesis ;
               drift:aboutDrift ?de ;
               drift:proposedTrigger ?trigger .
          OPTIONAL { ?hyp drift:confidence ?conf }
          OPTIONAL {
            ?hyp drift:evidenceType ?evType .
            OPTIONAL { ?evType skos:prefLabel ?evLabel FILTER (lang(?evLabel) = "en") }
          }
        }
        ORDER BY ?de ?trigger
        """)
    # index: de_id -> list[{triggerLabel, triggerYear (None), category (None), evidence, confidence}]
    # (triggerYear and category are resolved later from trigger_map in build_graph_document)
    hyp_map: dict[str, dict[str, dict]] = defaultdict(dict)  # de_id -> trigger_id -> hyp_dict
    for r in hyp_rows:
        de_id = _val(r.get("de"))
        trig = _val(r.get("trigger"))
        if not de_id or not trig:
            continue
        if trig not in hyp_map[de_id]:
            hyp_map[de_id][trig] = {
                "confidence": _float_val(r.get("conf")),
                "evidenceLabels": [],
            }
        ev_label = _val(r.get("evLabel")) or _val(r.get("evType"))
        if ev_label and ev_label not in hyp_map[de_id][trig]["evidenceLabels"]:
            hyp_map[de_id][trig]["evidenceLabels"].append(ev_label)

    # Legacy fallback: direct drift:triggeredBy (old data may use this).
    legacy_rows = kg.query(PREFIXES + """
        SELECT ?de ?trigger
        WHERE {
          ?de a drift:DriftEvent ;
              drift:triggeredBy ?trigger .
        }
        """)
    for r in legacy_rows:
        de_id = _val(r.get("de"))
        trig = _val(r.get("trigger"))
        if de_id and trig and trig not in hyp_map[de_id]:
            hyp_map[de_id][trig] = {"confidence": None, "evidenceLabels": []}

    # Assemble final drift event records.
    de_map: dict[str, dict] = {}
    for row in base_rows:
        de_id = _val(row.get("de"))
        if not de_id:
            continue
        word_id = _val(row.get("word"))
        if not word_id:
            continue

        year = _int_val(row.get("year"))
        year_end: int | None = None
        if year is None and de_id in interval_map:
            year, year_end = interval_map[de_id]

        # Accumulate drift types; later rows for same de may add new types.
        types = dtype_map.get(de_id, [])
        type_ids = [t[0] for t in types]
        type_labels = [t[1] or t[0].rsplit("#", 1)[-1] for t in types]
        drift_type_label = ", ".join(type_labels) if type_labels else None

        trigger_ids = sorted(hyp_map.get(de_id, {}).keys())

        confidence = _float_val(row.get("confidence"))

        if de_id not in de_map:
            de_map[de_id] = {
                "id": de_id,
                "wordId": word_id,
                "senseFromId": _val(row.get("senseFrom")),
                "senseToId": _val(row.get("senseTo")),
                "driftTypeLabel": drift_type_label,
                "driftTypeIds": type_ids,
                "year": year,
                "yearEnd": year_end,
                "confidence": confidence,
                "triggerIds": trigger_ids,
            }

    return list(de_map.values())


# ---------------------------------------------------------------------------
# Query: words (with senses and frequency observations)
# ---------------------------------------------------------------------------


def build_words(
    kg: "KG",
    drift_event_map: dict[str, dict],
) -> list[dict]:
    """Return all drift:Word nodes with senses and frequency observations.

    Parameters
    ----------
    kg:
        Trails KG object (from ``ctx.kg``).
    drift_event_map:
        Pre-built map of drift-event-id → drift-event-dict (from
        :func:`build_drift_events`). Passed in to avoid re-querying.

    Returns
    -------
    list[dict]
        Each dict is a FULL word object (LIGHT + HEAVY fields).
        See DATA-CONTRACT.md for the field schema.
    """
    # Word base attributes.
    word_rows = kg.query(PREFIXES + """
        SELECT DISTINCT ?word ?writtenForm ?language
        WHERE {
          ?word a drift:Word .
          OPTIONAL { ?word drift:writtenForm ?writtenForm }
          OPTIONAL { ?word drift:language ?language }
        }
        ORDER BY ?word
        """)

    # Senses per word.
    sense_rows = kg.query(PREFIXES + """
        SELECT ?word ?sense ?glossEn ?glossAny ?connotation ?connotationLabel ?firstAttested
        WHERE {
          ?word a drift:Word ;
                ontolex:sense ?sense .
          OPTIONAL { ?sense drift:gloss ?glossEn FILTER (lang(?glossEn) = "en") }
          OPTIONAL { ?sense drift:gloss ?glossAny }
          OPTIONAL { ?sense drift:connotation ?connotation }
          OPTIONAL {
            ?sense drift:connotation ?connotation .
            ?connotation skos:prefLabel ?connotationLabel FILTER (lang(?connotationLabel) = "en")
          }
          OPTIONAL { ?sense drift:firstAttested ?firstAttested }
        }
        ORDER BY ?word ?sense
        """)

    # Sense attested intervals.
    sense_interval_rows = kg.query(PREFIXES + """
        SELECT ?sense ?beginYear ?endYear
        WHERE {
          ?sense a drift:Sense ;
                 drift:attestedDuring ?interval .
          OPTIONAL {
            ?interval time:hasBeginning ?begin .
            ?begin time:inXSDgYear ?beginYear .
          }
          OPTIONAL {
            ?interval time:hasEnd ?end .
            ?end time:inXSDgYear ?endYear .
          }
        }
        """)
    sense_interval_map: dict[str, tuple[int | None, int | None]] = {}
    for r in sense_interval_rows:
        sid = _val(r.get("sense"))
        if sid:
            sense_interval_map[sid] = (
                _int_val(r.get("beginYear")),
                _int_val(r.get("endYear")),
            )

    # Frequency observations per word.
    freq_rows = kg.query(PREFIXES + """
        SELECT ?word ?year ?freq
        WHERE {
          ?obs a drift:FrequencyObservation ;
               drift:ofWord ?word ;
               drift:observedYear ?year ;
               drift:relativeFrequency ?freq .
        }
        ORDER BY ?word ?year
        """)

    # Cross-lingual links.
    xling_rows = kg.query(PREFIXES + """
        SELECT ?word ?xLing
        WHERE {
          ?word a drift:Word ;
                drift:crossLingualOf ?xLing .
        }
        """)

    # Build sense cache.
    sense_cache: dict[str, dict] = {}
    word_to_sense_ids: dict[str, list[str]] = defaultdict(list)

    for r in sense_rows:
        word_id = _val(r.get("word"))
        sense_id = _val(r.get("sense"))
        if not word_id or not sense_id:
            continue

        if sense_id not in word_to_sense_ids[word_id]:
            word_to_sense_ids[word_id].append(sense_id)

        if sense_id in sense_cache:
            # Fill in optional fields that may appear in a later row.
            existing = sense_cache[sense_id]
            if existing["glossEn"] is None:
                gloss = _val(r.get("glossEn")) or _val(r.get("glossAny"))
                if gloss:
                    existing["glossEn"] = gloss
            if existing["connotation"] is None:
                existing["connotation"] = _val(r.get("connotationLabel")) or _val(r.get("connotation"))
                existing["connotationId"] = _val(r.get("connotation"))
            continue

        interval = sense_interval_map.get(sense_id, (None, None))
        gloss = _val(r.get("glossEn")) or _val(r.get("glossAny"))
        conn_label = _val(r.get("connotationLabel"))
        conn_id = _val(r.get("connotation"))
        # When only the concept IRI is available (no prefLabel), use it raw.
        if conn_label is None and conn_id:
            conn_label = conn_id.rsplit("#", 1)[-1]

        sense_cache[sense_id] = {
            "id": sense_id,
            "glossEn": gloss,
            "connotation": conn_label,
            "connotationId": conn_id,
            "firstAttested": _int_val(r.get("firstAttested")),
            "attestedIntervalStart": interval[0],
            "attestedIntervalEnd": interval[1],
        }

    # Build frequency index.
    word_to_freq: dict[str, list[dict]] = defaultdict(list)
    for r in freq_rows:
        word_id = _val(r.get("word"))
        year = _int_val(r.get("year"))
        freq = _float_val(r.get("freq"))
        if word_id and year is not None and freq is not None:
            word_to_freq[word_id].append({"year": year, "value": freq})
    for freq_list in word_to_freq.values():
        freq_list.sort(key=lambda x: x["year"])

    # Build drift-event index by word.
    word_to_drift_ids: dict[str, list[str]] = defaultdict(list)
    for de in drift_event_map.values():
        word_to_drift_ids[de["wordId"]].append(de["id"])

    # Build cross-lingual raw links.
    cross_lingual_raw: dict[str, set[str]] = defaultdict(set)
    for r in xling_rows:
        word_id = _val(r.get("word"))
        x_id = _val(r.get("xLing"))
        if word_id and x_id and word_id != x_id:
            cross_lingual_raw[word_id].add(x_id)
            cross_lingual_raw[x_id].add(word_id)

    # Assemble raw word candidates.
    QUALITY_RANK = {"high": 0, "benchmark": 1, "detected": 2}

    raw_candidates: list[dict] = []
    raw_count = 0

    for row in word_rows:
        word_id = _val(row.get("word"))
        if not word_id:
            continue
        raw_count += 1

        written_form_raw = _val(row.get("writtenForm"))
        sense_ids = word_to_sense_ids.get(word_id, [])
        if written_form_raw is None and not sense_ids:
            continue
        written_form = written_form_raw or word_id.rsplit("/", 1)[-1].rsplit("#", 1)[-1]

        language = _val(row.get("language"))

        senses = [sense_cache[s] for s in sense_ids if s in sense_cache]
        senses.sort(key=lambda s: s["firstAttested"] or 0)

        drift_ids = word_to_drift_ids.get(word_id, [])
        drifts = [drift_event_map[d] for d in drift_ids if d in drift_event_map]
        drifts.sort(key=lambda d: d["year"] or 0)

        freq_obs = word_to_freq.get(word_id, [])

        source = derive_source(word_id)
        quality = derive_quality(source)

        raw_candidates.append({
            "id": word_id,
            "writtenForm": written_form,
            "language": language,
            "senses": senses,
            "driftEvents": drifts,
            "frequencyObservations": freq_obs,
            "source": source,
            "quality": quality,
            "sources": [source],
            "crossLingualOf": sorted(cross_lingual_raw.get(word_id, ())),
        })

    logger.debug("raw Word nodes: %d", raw_count)

    # Deduplicate by (writtenForm.lower(), language) — same logic as original.
    dedup_map: dict[tuple, dict] = {}
    merge_count = 0

    for cand in raw_candidates:
        key = (cand["writtenForm"].lower(), cand["language"])
        existing = dedup_map.get(key)
        if existing is None:
            dedup_map[key] = cand
            continue

        merge_count += 1
        # Union sources.
        existing["sources"] = sorted(set(existing["sources"]) | set(cand["sources"]))
        # Upgrade quality.
        if QUALITY_RANK.get(cand["quality"], 2) < QUALITY_RANK.get(existing["quality"], 2):
            existing["quality"] = cand["quality"]
            existing["source"] = cand["source"]
        # Union drift events.
        existing_de_ids = {d["id"] for d in existing["driftEvents"]}
        for de in cand["driftEvents"]:
            if de["id"] not in existing_de_ids:
                existing["driftEvents"].append(de)
                existing_de_ids.add(de["id"])
        existing["driftEvents"].sort(key=lambda d: d["year"] or 0)
        # Union senses.
        existing_s_ids = {s["id"] for s in existing["senses"]}
        for se in cand["senses"]:
            if se["id"] not in existing_s_ids:
                existing["senses"].append(se)
                existing_s_ids.add(se["id"])
        existing["senses"].sort(key=lambda s: s["firstAttested"] or 0)
        # Union cross-lingual.
        existing["crossLingualOf"] = sorted(
            set(existing["crossLingualOf"]) | set(cand["crossLingualOf"])
        )
        # Union freq obs.
        existing_years = {o["year"] for o in existing["frequencyObservations"]}
        for fo in cand["frequencyObservations"]:
            if fo["year"] not in existing_years:
                existing["frequencyObservations"].append(fo)
                existing_years.add(fo["year"])
        existing["frequencyObservations"].sort(key=lambda o: o["year"])

    # Canonicalise cross-lingual IRIs across the deduped set.
    raw_to_canonical: dict[str, str] = {}
    for kept in dedup_map.values():
        raw_to_canonical[kept["id"]] = kept["id"]
    for cand in raw_candidates:
        canon = dedup_map.get((cand["writtenForm"].lower(), cand["language"]))
        if canon is not None:
            raw_to_canonical[cand["id"]] = canon["id"]

    canonical_links: dict[str, set[str]] = defaultdict(set)
    valid_ids = {kept["id"] for kept in dedup_map.values()}
    for kept in dedup_map.values():
        for raw_target in kept["crossLingualOf"]:
            tgt = raw_to_canonical.get(raw_target, raw_target)
            if tgt != kept["id"]:
                canonical_links[kept["id"]].add(tgt)
                canonical_links[tgt].add(kept["id"])
    for kept in dedup_map.values():
        kept["crossLingualOf"] = sorted(
            t for t in canonical_links.get(kept["id"], ()) if t in valid_ids
        )

    words_list = sorted(
        dedup_map.values(),
        key=lambda w: (w["language"] != "en", w["writtenForm"].lower()),
    )

    logger.info(
        "words: raw=%d deduped=%d merged=%d", raw_count, len(words_list), merge_count
    )

    return words_list, raw_count, merge_count


# ---------------------------------------------------------------------------
# Query: SKOS drift types
# ---------------------------------------------------------------------------


def build_drift_types(kg: "KG") -> list[dict]:
    """Return all drift:DriftTypeScheme SKOS concepts.

    Returns
    -------
    list[dict]
        Each dict has keys: ``id``, ``label``, ``broaderId``,
        ``broaderLabel``.  Sorted by (broaderLabel, label).
    """
    rows = kg.query(PREFIXES + """
        SELECT DISTINCT ?concept ?label ?broader ?broaderLabel
        WHERE {
          ?concept a skos:Concept ;
                   skos:inScheme drift:DriftTypeScheme .
          OPTIONAL { ?concept skos:prefLabel ?label FILTER (lang(?label) = "en") }
          OPTIONAL { ?concept skos:prefLabel ?label }
          OPTIONAL {
            ?concept skos:broader ?broader .
            OPTIONAL { ?broader skos:prefLabel ?broaderLabel FILTER (lang(?broaderLabel) = "en") }
            OPTIONAL { ?broader skos:prefLabel ?broaderLabel }
          }
        }
        """)

    seen: dict[str, dict] = {}
    for r in rows:
        c_id = _val(r.get("concept"))
        if not c_id:
            continue
        if c_id not in seen:
            label = _val(r.get("label")) or c_id.rsplit("#", 1)[-1]
            broader_id = _val(r.get("broader"))
            broader_label = _val(r.get("broaderLabel"))
            seen[c_id] = {
                "id": c_id,
                "label": label,
                "broaderId": broader_id,
                "broaderLabel": broader_label,
            }
        else:
            existing = seen[c_id]
            if existing["broaderLabel"] is None:
                bl = _val(r.get("broaderLabel"))
                if bl:
                    existing["broaderLabel"] = bl

    return sorted(
        seen.values(),
        key=lambda dt: (dt.get("broaderLabel") or "", dt.get("label") or ""),
    )


# ---------------------------------------------------------------------------
# Aggregate builders
# ---------------------------------------------------------------------------


def build_by_decade_type(drift_events_flat: list[dict]) -> list[dict]:
    """Build stacked histogram ``[{decade, type, n}]``.

    Parameters
    ----------
    drift_events_flat:
        The flat drift-event list produced by :func:`_build_drift_events_flat`.
    """
    counts: Counter = Counter()
    for fe in drift_events_flat:
        if fe["year"] is None:
            continue
        decade = (fe["year"] // 10) * 10
        raw_type = fe["type"] or "unknown"
        for t in raw_type.split(","):
            t = t.strip()
            if t:
                counts[(decade, t)] += 1
    return [
        {"decade": k[0], "type": k[1], "n": v}
        for k, v in sorted(counts.items())
    ]


def build_trigger_impact(
    triggers: list[dict],
    words_list: list[dict],
) -> list[dict]:
    """Build per-trigger rollup ``[{trigger, label, year, category, wordCount, words}]``.

    Parameters
    ----------
    triggers:
        List of trigger dicts from :func:`build_triggers`.
    words_list:
        Full deduped word list (needed to map drift-event trigger ids to forms).
    """
    trigger_word_map: dict[str, list[str]] = defaultdict(list)
    for word in words_list:
        word_form = word["writtenForm"]
        for de in word["driftEvents"]:
            for tid in de["triggerIds"]:
                if word_form not in trigger_word_map[tid]:
                    trigger_word_map[tid].append(word_form)

    result: list[dict] = []
    for te in triggers:
        affected = trigger_word_map.get(te["id"], [])
        result.append({
            "trigger": te["id"],
            "label": te["label"],
            "year": te["date"],
            "category": te["category"],
            "wordCount": len(affected),
            "words": sorted(affected),
        })
    result.sort(key=lambda t: (-(t["wordCount"]), t["year"] or 0))
    return result


def build_facets(
    words_list: list[dict],
    drift_events_flat: list[dict],
    kg: "KG",
) -> dict:
    """Build distinct filter-value facets for the explorer UI.

    Parameters
    ----------
    words_list:
        Full deduped word list.
    drift_events_flat:
        Flat drift-event list.
    kg:
        Trails KG object (needed for evidence-type SKOS concepts).

    Returns
    -------
    dict
        Keys: ``language``, ``driftType``, ``connotation``,
        ``evidenceType``, ``source``, ``quality``.
    """
    # Languages.
    all_langs = sorted({w["language"] or "?" for w in words_list})

    # Drift types (from flat events).
    all_drift_types: list[str] = []
    seen_dt: set[str] = set()
    for fe in drift_events_flat:
        for t in (fe["type"] or "unknown").split(","):
            t = t.strip()
            if t and t not in seen_dt:
                seen_dt.add(t)
                all_drift_types.append(t)
    all_drift_types.sort()

    # Connotations (from senses).
    all_connotations = sorted({
        s["connotation"]
        for w in words_list
        for s in w["senses"]
        if s["connotation"]
    })

    # Evidence types from SKOS.
    ev_rows = kg.query(PREFIXES + """
        SELECT DISTINCT ?concept ?label
        WHERE {
          ?concept a skos:Concept ;
                   skos:inScheme drift:EvidenceTypeScheme .
          OPTIONAL { ?concept skos:prefLabel ?label FILTER (lang(?label) = "en") }
          OPTIONAL { ?concept skos:prefLabel ?label }
        }
        """)
    evidence_types: list[str] = []
    for r in ev_rows:
        label = _val(r.get("label"))
        if label:
            evidence_types.append(label)
    evidence_types.sort()

    SOURCE_ORDER = ["Curated", "GfdS", "OWID", "DWUG", "SemEval", "Frequency"]
    QUALITY_ORDER = ["high", "benchmark", "detected"]
    all_sources = sorted(
        {w["source"] for w in words_list},
        key=lambda s: SOURCE_ORDER.index(s) if s in SOURCE_ORDER else 99,
    )
    all_qualities = sorted(
        {w["quality"] for w in words_list},
        key=lambda q: QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 99,
    )

    return {
        "language": all_langs,
        "driftType": all_drift_types,
        "connotation": all_connotations,
        "evidenceType": evidence_types,
        "source": all_sources,
        "quality": all_qualities,
    }


# ---------------------------------------------------------------------------
# Causal hypothesis index (for driftEventsFlat)
# ---------------------------------------------------------------------------


def _build_causal_index(
    kg: "KG",
    trigger_map: dict[str, dict],
) -> dict[str, list[dict]]:
    """Build de_id → list of hypothesis metadata dicts.

    Used to populate the ``causes`` field in driftEventsFlat.
    """
    rows = kg.query(PREFIXES + """
        SELECT ?de ?trigger ?conf ?evType ?evLabel
        WHERE {
          ?hyp a drift:CausalHypothesis ;
               drift:aboutDrift ?de ;
               drift:proposedTrigger ?trigger .
          OPTIONAL { ?hyp drift:confidence ?conf }
          OPTIONAL {
            ?hyp drift:evidenceType ?evType .
            OPTIONAL { ?evType skos:prefLabel ?evLabel FILTER (lang(?evLabel) = "en") }
          }
        }
        ORDER BY ?de ?trigger
        """)

    # Collapse per (de, trigger) pair.
    index: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        de_id = _val(r.get("de"))
        trig_id = _val(r.get("trigger"))
        if not de_id or not trig_id:
            continue
        if trig_id not in index[de_id]:
            te = trigger_map.get(trig_id, {})
            index[de_id][trig_id] = {
                "triggerLabel": te.get("label", trig_id.rsplit("/", 1)[-1]),
                "triggerYear": te.get("date"),
                "category": te.get("category"),
                "evidence": [],
                "confidence": _float_val(r.get("conf")),
            }
        ev_label = _val(r.get("evLabel")) or _val(r.get("evType"))
        if ev_label and ev_label not in index[de_id][trig_id]["evidence"]:
            index[de_id][trig_id]["evidence"].append(ev_label)

    result: dict[str, list[dict]] = {}
    for de_id, trig_dict in index.items():
        hyps = sorted(trig_dict.values(), key=lambda h: -(h["confidence"] or 0))
        result[de_id] = hyps
    return result


# ---------------------------------------------------------------------------
# Main document builder
# ---------------------------------------------------------------------------


def build_graph_document(kg: "KG") -> dict:
    """Build the full graph document (same structure as graph.json).

    This is the main entry point.  Call :func:`split_document` on the
    result to obtain the (core, detail) pair for the explorer.

    Parameters
    ----------
    kg:
        A Trails ``KG`` object (from ``ctx.kg``).

    Returns
    -------
    dict
        Keys: ``words``, ``triggers``, ``driftTypes``, ``meta``,
        ``driftEventsFlat``, ``byDecadeType``, ``triggerImpact``,
        ``facets``.
    """
    logger.info("building trigger list …")
    triggers = build_triggers(kg)
    trigger_map = {t["id"]: t for t in triggers}

    logger.info("building drift events …")
    drift_events = build_drift_events(kg)
    drift_event_map = {de["id"]: de for de in drift_events}

    logger.info("building words …")
    words_list, raw_count, merge_count = build_words(kg, drift_event_map)

    logger.info("building drift types …")
    drift_types = build_drift_types(kg)

    logger.info("building causal index …")
    causal_index = _build_causal_index(kg, trigger_map)

    # Sense connotation quick-lookup.
    sense_conn: dict[str, str | None] = {
        s["id"]: s["connotation"]
        for w in words_list
        for s in w["senses"]
    }

    # -- driftEventsFlat --
    drift_events_flat: list[dict] = []
    for word in words_list:
        for de in word["driftEvents"]:
            from_conn = (
                sense_conn.get(de["senseFromId"]) if de.get("senseFromId") else None
            )
            to_conn = (
                sense_conn.get(de["senseToId"]) if de.get("senseToId") else None
            )
            causes = causal_index.get(de["id"], [])
            drift_events_flat.append({
                "word": word["writtenForm"],
                "lang": word["language"] or "?",
                "type": de["driftTypeLabel"] or "unknown",
                "year": de["year"],
                "fromConn": from_conn,
                "toConn": to_conn,
                "hasTrigger": len(de["triggerIds"]) > 0,
                "causes": causes,
                "source": word["source"],
                "quality": word["quality"],
            })
    drift_events_flat.sort(key=lambda e: (e["year"] or 0, e["word"]))

    # -- byDecadeType --
    by_decade_type = build_by_decade_type(drift_events_flat)

    # -- triggerImpact --
    trigger_impact = build_trigger_impact(triggers, words_list)

    # -- facets --
    facets = build_facets(words_list, drift_events_flat, kg)

    # -- meta --
    total_drift_events = sum(len(w["driftEvents"]) for w in words_list)
    by_language: dict[str, int] = {}
    by_source: dict[str, int] = {}
    by_quality: dict[str, int] = {}
    for w in words_list:
        lang = w["language"] or "?"
        by_language[lang] = by_language.get(lang, 0) + 1
        by_source[w["source"]] = by_source.get(w["source"], 0) + 1
        by_quality[w["quality"]] = by_quality.get(w["quality"], 0) + 1

    meta = {
        "words": len(words_list),
        "rawWordNodes": raw_count,
        "mergedDuplicates": merge_count,
        "byLanguage": by_language,
        "bySource": by_source,
        "byQuality": by_quality,
        "driftEvents": total_drift_events,
        "triggers": len(triggers),
    }

    return {
        "words": words_list,
        "triggers": sorted(triggers, key=lambda t: t.get("date") or 0),
        "driftTypes": drift_types,
        "meta": meta,
        "driftEventsFlat": drift_events_flat,
        "byDecadeType": by_decade_type,
        "triggerImpact": trigger_impact,
        "facets": facets,
    }


# ---------------------------------------------------------------------------
# Document split (core + detail)
# ---------------------------------------------------------------------------


def split_document(doc: dict) -> tuple[dict, dict]:
    """Split the full graph document into (core, detail).

    ``core`` contains everything needed for first paint, with LIGHT
    word objects (no heavy per-word detail).  ``detail`` is a map of
    ``wordId -> {senses, driftEvents, frequencyObservations, sources}``.

    This is a pure re-projection of *doc*: no field meaning changes.
    Identical to the original ``viz/export.py`` ``split_document()``.

    Parameters
    ----------
    doc:
        Full document dict from :func:`build_graph_document`.

    Returns
    -------
    tuple[dict, dict]
        ``(core_doc, detail_map)``
    """
    light_words: list[dict] = []
    detail_map: dict[str, dict] = {}

    for w in doc["words"]:
        # Distinct drift-type labels (split comma-joined strings).
        drift_type_labels: list[str] = []
        seen_dt: set[str] = set()
        has_trigger = False
        for de in w["driftEvents"]:
            if de.get("triggerIds"):
                has_trigger = True
            label = de.get("driftTypeLabel")
            if label:
                for t in label.split(","):
                    t = t.strip()
                    if t and t not in seen_dt:
                        seen_dt.add(t)
                        drift_type_labels.append(t)
        drift_type_labels.sort()

        # Year span across senses, drift events, frequency observations.
        years: list[int] = []
        for s in w["senses"]:
            for key in ("firstAttested", "attestedIntervalStart", "attestedIntervalEnd"):
                v = s.get(key)
                if v is not None:
                    years.append(v)
        for de in w["driftEvents"]:
            for key in ("year", "yearEnd"):
                v = de.get(key)
                if v is not None:
                    years.append(v)
        for fo in w["frequencyObservations"]:
            v = fo.get("year")
            if v is not None:
                years.append(v)
        year_start = min(years) if years else None
        year_end = max(years) if years else None

        light_words.append({
            "id": w["id"],
            "writtenForm": w["writtenForm"],
            "language": w["language"],
            "source": w["source"],
            "quality": w["quality"],
            "sources": w["sources"],
            "driftTypeLabels": drift_type_labels,
            "yearStart": year_start,
            "yearEnd": year_end,
            "hasTrigger": has_trigger,
            "crossLingualOf": w.get("crossLingualOf", []),
        })

        detail_map[w["id"]] = {
            "senses": w["senses"],
            "driftEvents": w["driftEvents"],
            "frequencyObservations": w["frequencyObservations"],
            "sources": w["sources"],
        }

    core = {
        "meta": doc["meta"],
        "driftTypes": doc["driftTypes"],
        "facets": doc["facets"],
        "byDecadeType": doc["byDecadeType"],
        "triggerImpact": doc["triggerImpact"],
        "triggers": doc["triggers"],
        "driftEventsFlat": doc["driftEventsFlat"],
        "words": light_words,
    }

    return core, detail_map
