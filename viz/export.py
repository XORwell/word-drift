#!/usr/bin/env python3
"""
export.py -- WORD-DRIFT viz export
Loads ontology/*.ttl + examples/*.ttl + data/**/*.ttl (recursive),
runs SPARQL queries, and writes viz/data/graph.json plus a split pair
viz/data/graph-core.json + viz/data/graph-detail.json (for fast first paint).

Usage:
    python viz/export.py

============================================================================
JSON OUTPUT CONTRACT  (see also site/DATA-CONTRACT.md)
============================================================================

The exporter emits THREE files into viz/data/ (copied verbatim into site/):

1. graph.json        -- FULL union document (back-compat, unchanged shape).
2. graph-core.json   -- everything needed for first paint, NO heavy per-word
                        detail. This is what the explorer loads up front.
3. graph-detail.json -- a map { wordId -> heavy per-word fields }, fetched
                        lazily / in the background after first paint.

graph.json (full, unchanged) top-level keys:
    words            list of FULL word objects (see below, heavy fields included)
    triggers         list of trigger-event objects
    driftTypes       list of SKOS drift-type concepts
    meta             summary counts
    driftEventsFlat  flat list of drift-event records (overview timeline + joins)
    byDecadeType     stacked histogram [{decade, type, n}]
    triggerImpact    per-trigger impact rollup
    facets           distinct filter values

A FULL word object (as in graph.json["words"][i]) has:
    id, writtenForm, language, source, quality, sources (list),
    crossLingualOf (list[str] of word ids)                        <- LIGHT fields
    senses                 (list)   <- HEAVY
    driftEvents            (list)   <- HEAVY
    frequencyObservations  (list)   <- HEAVY

----------------------------------------------------------------------------
graph-core.json top-level keys (SAME shapes as in graph.json, minus heavy
word detail):
    meta             identical to graph.json["meta"]
    driftTypes       identical to graph.json["driftTypes"]
    facets           identical to graph.json["facets"]
    byDecadeType     identical to graph.json["byDecadeType"]
    triggerImpact    identical to graph.json["triggerImpact"]
    triggers         identical to graph.json["triggers"]  (small, included full)
    driftEventsFlat  identical to graph.json["driftEventsFlat"]
    words            list of LIGHT word objects, one per word:
        {
          id:              str   (word IRI; key into graph-detail.json)
          writtenForm:     str
          language:        str | null
          source:          str   (primary source label)
          quality:         str   ("high" | "benchmark" | "detected")
          sources:         list[str]   (union of all source labels)
          driftTypeLabels: list[str]   (distinct drift-type labels for this word)
          yearStart:       int | null  (earliest year across senses/drifts/freq)
          yearEnd:         int | null  (latest year across senses/drifts/freq)
          hasTrigger:      bool        (true if any drift event has a trigger)
          crossLingualOf:  list[str]   (word ids of EXPLICIT cross-lingual
                                        equivalents via drift:crossLingualOf;
                                        symmetrised; NOT inferred from triggers)
        }
    NOTE: a LIGHT word does NOT carry senses / driftEvents /
          frequencyObservations. Fetch those from graph-detail.json by id.

----------------------------------------------------------------------------
graph-detail.json: a single JSON object (map) keyed by word id:
    {
      "<wordId>": {
          senses:                list   (identical to the word's full senses)
          driftEvents:           list   (identical to the word's full driftEvents)
          frequencyObservations: list   (identical to the word's full freq obs)
          sources:               list[str]  (union of source labels; convenience)
      },
      ...
    }
    Every word id present in graph-core.json["words"] has exactly one entry here.
============================================================================
"""

import json
import pathlib
import sys
from collections import defaultdict

import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, OWL, XSD

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
DRIFT = Namespace("https://w3id.org/word-drift/ontology#")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
TIME = Namespace("http://www.w3.org/2006/time#")
DCT = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")

# ---------------------------------------------------------------------------
# Locate project root relative to this script
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUT_DIR = SCRIPT_DIR / "data"
OUT_FILE = OUT_DIR / "graph.json"
CORE_FILE = OUT_DIR / "graph-core.json"
DETAIL_FILE = OUT_DIR / "graph-detail.json"


# ---------------------------------------------------------------------------
# Source / quality derivation from wdr: IRI
# ---------------------------------------------------------------------------

def derive_source(word_uri: str) -> str:
    """Map a wdr: IRI to a human-readable source label."""
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
    """Map source label to a quality tier."""
    if source in ("GfdS", "OWID", "Curated"):
        return "high"
    if source in ("DWUG", "SemEval"):
        return "benchmark"
    # Frequency
    return "detected"


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph() -> Graph:
    g = Graph()
    g.bind("drift", DRIFT)
    g.bind("ontolex", ONTOLEX)
    g.bind("time", TIME)
    g.bind("dct", DCT)
    g.bind("skos", SKOS)
    g.bind("owl", OWL)

    # Load ontology modules first (vocabulary / labels needed by SPARQL)
    ont_dir = ROOT / "ontology"
    for ttl in sorted(ont_dir.glob("*.ttl")):
        g.parse(ttl, format="turtle")

    # Load examples
    ex_dir = ROOT / "examples"
    for ttl in sorted(ex_dir.glob("*.ttl")):
        g.parse(ttl, format="turtle")

    # Load data/ recursively (top-level *.ttl + all sub-dirs)
    data_dir = ROOT / "data"
    if data_dir.is_dir():
        for ttl in sorted(data_dir.rglob("*.ttl")):
            g.parse(ttl, format="turtle")

    return g


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def uri_local(uri: URIRef) -> str:
    """Return the local fragment or path segment of a URI."""
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            return s.rsplit(sep, 1)[-1]
    return s


def get_pref_label(g: Graph, concept: URIRef, lang: str = "en") -> str | None:
    for label in g.objects(concept, SKOS.prefLabel):
        if isinstance(label, Literal) and label.language == lang:
            return str(label)
    for label in g.objects(concept, SKOS.prefLabel):
        if isinstance(label, Literal):
            return str(label)
    for label in g.objects(concept, RDFS.label):
        if isinstance(label, Literal) and (label.language == lang or not label.language):
            return str(label)
    return uri_local(concept)


def get_year(value) -> int | None:
    """Parse an xsd:gYear literal to int, or return None."""
    if value is None:
        return None
    s = str(value)
    try:
        return int(s.lstrip("+"))
    except ValueError:
        return None


def get_gloss(g: Graph, sense: URIRef, lang: str = "en") -> str | None:
    for gloss in g.objects(sense, DRIFT.gloss):
        if isinstance(gloss, Literal) and gloss.language == lang:
            return str(gloss)
    for gloss in g.objects(sense, DRIFT.gloss):
        if isinstance(gloss, Literal):
            return str(gloss)
    return None


# ---------------------------------------------------------------------------
# Build JSON document
# ---------------------------------------------------------------------------

def build_document(g: Graph) -> dict:
    # -- 1. Collect all trigger events -----------------------------------------
    trigger_map: dict[str, dict] = {}
    for te in sorted(g.subjects(RDF.type, DRIFT.TriggerEvent), key=str):
        te_id = str(te)
        label_en = None
        for label in g.objects(te, RDFS.label):
            if isinstance(label, Literal) and label.language == "en":
                label_en = str(label)
                break
        if label_en is None:
            for label in g.objects(te, RDFS.label):
                if isinstance(label, Literal):
                    label_en = str(label)
                    break
        if label_en is None:
            label_en = uri_local(te)

        cat_node = g.value(te, DRIFT.triggerCategory)
        category = get_pref_label(g, cat_node) if cat_node else None

        date_lit = g.value(te, DRIFT.eventDate)
        date_year = get_year(date_lit)

        same_as = [str(o) for o in g.objects(te, OWL.sameAs)]

        desc = g.value(te, DCT.description)
        description = str(desc) if desc else None

        trigger_map[te_id] = {
            "id": te_id,
            "label": label_en,
            "date": date_year,
            "category": category,
            "wikidataSameAs": same_as[0] if same_as else None,
            "description": description,
        }

    # -- 2. Collect all drift events and index by word -------------------------
    drift_event_map: dict[str, dict] = {}
    word_to_drifts: dict[str, list[str]] = defaultdict(list)

    for de in sorted(g.subjects(RDF.type, DRIFT.DriftEvent), key=str):
        de_id = str(de)

        word_node = g.value(de, DRIFT.affectsWord)
        if word_node is None:
            continue
        word_id = str(word_node)

        sense_from = g.value(de, DRIFT.senseFrom)
        sense_to = g.value(de, DRIFT.senseTo)

        drift_type_nodes = sorted(g.objects(de, DRIFT.driftType), key=str)
        drift_type_labels = [get_pref_label(g, dt) for dt in drift_type_nodes]
        drift_type_node = drift_type_nodes[0] if drift_type_nodes else None
        drift_type_label = ", ".join(drift_type_labels) if drift_type_labels else None

        drift_year_lit = g.value(de, DRIFT.driftYear)
        drift_year = get_year(drift_year_lit)
        drift_year_end = None
        if drift_year is None:
            interval = g.value(de, DRIFT.driftInterval)
            if interval:
                begin = g.value(interval, TIME.hasBeginning)
                if begin:
                    y_lit = g.value(begin, TIME.inXSDgYear)
                    drift_year = get_year(y_lit)
                end = g.value(interval, TIME.hasEnd)
                if end:
                    y_lit = g.value(end, TIME.inXSDgYear)
                    drift_year_end = get_year(y_lit)

        confidence_lit = g.value(de, DRIFT.confidence)
        confidence = float(str(confidence_lit)) if confidence_lit else None

        # Triggers are reified through drift:CausalHypothesis (ADR-0004): the link
        # is  de  <-drift:aboutDrift- hyp -drift:proposedTrigger-> trigger .
        # (The legacy drift:triggeredBy shortcut was removed; keep it as a fallback
        # so any older data still resolves.)
        trigger_ids: list[str] = []
        for hyp in g.subjects(DRIFT.aboutDrift, de):
            tnode = g.value(hyp, DRIFT.proposedTrigger)
            if tnode is not None and str(tnode) not in trigger_ids:
                trigger_ids.append(str(tnode))
        for t in g.objects(de, DRIFT.triggeredBy):
            if str(t) not in trigger_ids:
                trigger_ids.append(str(t))
        triggers = sorted(trigger_ids)

        drift_event_map[de_id] = {
            "id": de_id,
            "wordId": word_id,
            "senseFromId": str(sense_from) if sense_from else None,
            "senseToId": str(sense_to) if sense_to else None,
            "driftTypeLabel": drift_type_label,
            "driftTypeIds": [str(dt) for dt in drift_type_nodes],
            "year": drift_year,
            "yearEnd": drift_year_end,
            "confidence": confidence,
            "triggerIds": triggers,
        }
        word_to_drifts[word_id].append(de_id)

    # -- 3. Collect frequency observations indexed by word --------------------
    word_to_freq: dict[str, list[dict]] = defaultdict(list)
    for obs in sorted(g.subjects(RDF.type, DRIFT.FrequencyObservation), key=str):
        word_node = g.value(obs, DRIFT.ofWord)
        if word_node is None:
            continue
        year_lit = g.value(obs, DRIFT.observedYear)
        year = get_year(year_lit)
        freq_lit = g.value(obs, DRIFT.relativeFrequency)
        freq = float(str(freq_lit)) if freq_lit else None
        if year is not None and freq is not None:
            word_to_freq[str(word_node)].append({"year": year, "value": freq})

    for k in word_to_freq:
        word_to_freq[k].sort(key=lambda x: x["year"])

    # -- 4. Collect senses per word -------------------------------------------
    sense_map: dict[str, dict] = {}
    word_to_senses: dict[str, list[str]] = defaultdict(list)

    for word in sorted(g.subjects(RDF.type, DRIFT.Word), key=str):
        word_id = str(word)
        for sense in sorted(g.objects(word, ONTOLEX.sense), key=str):
            sense_id = str(sense)
            word_to_senses[word_id].append(sense_id)
            if sense_id in sense_map:
                continue

            gloss_en = get_gloss(g, sense, "en")
            if gloss_en is None:
                gloss_en = get_gloss(g, sense, "de")

            connotation_node = g.value(sense, DRIFT.connotation)
            connotation_label = get_pref_label(g, connotation_node) if connotation_node else None
            connotation_id = str(connotation_node) if connotation_node else None

            first_attested_lit = g.value(sense, DRIFT.firstAttested)
            first_attested = get_year(first_attested_lit)

            attested_interval_start = None
            attested_interval_end = None
            interval = g.value(sense, DRIFT.attestedDuring)
            if interval:
                begin = g.value(interval, TIME.hasBeginning)
                if begin:
                    y_lit = g.value(begin, TIME.inXSDgYear)
                    attested_interval_start = get_year(y_lit)
                end = g.value(interval, TIME.hasEnd)
                if end:
                    y_lit = g.value(end, TIME.inXSDgYear)
                    attested_interval_end = get_year(y_lit)

            sense_map[sense_id] = {
                "id": sense_id,
                "glossEn": gloss_en,
                "connotation": connotation_label,
                "connotationId": connotation_id,
                "firstAttested": first_attested,
                "attestedIntervalStart": attested_interval_start,
                "attestedIntervalEnd": attested_interval_end,
            }

    # -- 4b. Collect cross-lingual links (drift:crossLingualOf) ----------------
    # Explicit, curated translation-equivalence between Words (ADR: not inferred
    # from a shared trigger). Symmetric in the ontology; we symmetrise here too
    # so both sides carry the link even if only one side asserted it.
    cross_lingual: dict[str, set[str]] = defaultdict(set)
    for subj, obj in g.subject_objects(DRIFT.crossLingualOf):
        s_id, o_id = str(subj), str(obj)
        if s_id == o_id:
            continue
        cross_lingual[s_id].add(o_id)
        cross_lingual[o_id].add(s_id)

    # -- 5. Build words list with source/quality, then deduplicate by (form.lower(), lang) --

    # Raw candidate list -- one entry per Word node
    raw_candidates: list[dict] = []
    raw_count = 0
    for word in sorted(g.subjects(RDF.type, DRIFT.Word), key=str):
        word_id = str(word)
        raw_count += 1

        written_form = g.value(word, DRIFT.writtenForm)
        if written_form is None and not word_to_senses.get(word_id):
            continue
        written_form_str = str(written_form) if written_form else uri_local(word)

        lang_lit = g.value(word, DRIFT.language)
        language = str(lang_lit) if lang_lit else None

        senses = [sense_map[s] for s in word_to_senses.get(word_id, []) if s in sense_map]
        senses.sort(key=lambda s: s["firstAttested"] or 0)

        drifts = [drift_event_map[d] for d in word_to_drifts.get(word_id, []) if d in drift_event_map]
        drifts.sort(key=lambda d: d["year"] or 0)

        freq_obs = word_to_freq.get(word_id, [])

        source = derive_source(word_id)
        quality = derive_quality(source)

        raw_candidates.append({
            "id": word_id,
            "writtenForm": written_form_str,
            "language": language,
            "senses": senses,
            "driftEvents": drifts,
            "frequencyObservations": freq_obs,
            "source": source,
            "quality": quality,
            "sources": [source],   # will be unioned during merge
            "crossLingualOf": sorted(cross_lingual.get(word_id, ())),  # raw IRIs; canonicalised below
        })

    # Deduplicate by (writtenForm.lower(), language).
    # Merge strategy:
    #   - Keep richest driftEvents + senses (union by id, de-duped)
    #   - Keep richest gloss (from candidate with most drift events)
    #   - Union the sources list
    #   - Quality = best tier: high > benchmark > detected
    QUALITY_RANK = {"high": 0, "benchmark": 1, "detected": 2}

    dedup_map: dict[tuple, dict] = {}
    merge_count = 0

    for cand in raw_candidates:
        key = (cand["writtenForm"].lower(), cand["language"])
        existing = dedup_map.get(key)
        if existing is None:
            dedup_map[key] = cand
        else:
            merge_count += 1
            # Union sources
            existing_sources = set(existing["sources"])
            for s in cand["sources"]:
                existing_sources.add(s)
            existing["sources"] = sorted(existing_sources)

            # Upgrade quality to best tier
            if QUALITY_RANK.get(cand["quality"], 2) < QUALITY_RANK.get(existing["quality"], 2):
                existing["quality"] = cand["quality"]
                existing["source"] = cand["source"]

            # Union drift events (by id)
            existing_de_ids = {d["id"] for d in existing["driftEvents"]}
            for de in cand["driftEvents"]:
                if de["id"] not in existing_de_ids:
                    existing["driftEvents"].append(de)
                    existing_de_ids.add(de["id"])
            existing["driftEvents"].sort(key=lambda d: d["year"] or 0)

            # Union senses (by id)
            existing_sense_ids = {s["id"] for s in existing["senses"]}
            for se in cand["senses"]:
                if se["id"] not in existing_sense_ids:
                    existing["senses"].append(se)
                    existing_sense_ids.add(se["id"])
            existing["senses"].sort(key=lambda s: s["firstAttested"] or 0)

            # Union cross-lingual links (raw IRIs, canonicalised after dedup)
            existing["crossLingualOf"] = sorted(
                set(existing["crossLingualOf"]) | set(cand["crossLingualOf"])
            )

            # Union freq obs
            existing_freq_years = {o["year"] for o in existing["frequencyObservations"]}
            for fo in cand["frequencyObservations"]:
                if fo["year"] not in existing_freq_years:
                    existing["frequencyObservations"].append(fo)
                    existing_freq_years.add(fo["year"])
            existing["frequencyObservations"].sort(key=lambda o: o["year"])

    # Canonicalise cross-lingual IRIs to the kept (deduped) word id.
    # A raw candidate IRI may have been merged into a different kept id; map every
    # raw IRI to its surviving canonical id, then rewrite each word's links and
    # symmetrise across the deduped set (drop self-links and unresolved targets).
    raw_to_canonical: dict[str, str] = {}
    for kept in dedup_map.values():
        key = (kept["writtenForm"].lower(), kept["language"])
        raw_to_canonical[kept["id"]] = kept["id"]
    for cand in raw_candidates:
        canon = dedup_map.get((cand["writtenForm"].lower(), cand["language"]))
        if canon is not None:
            raw_to_canonical[cand["id"]] = canon["id"]

    canonical_links: dict[str, set[str]] = defaultdict(set)
    for kept in dedup_map.values():
        for raw_target in kept["crossLingualOf"]:
            tgt = raw_to_canonical.get(raw_target, raw_target)
            if tgt != kept["id"]:
                canonical_links[kept["id"]].add(tgt)
                canonical_links[tgt].add(kept["id"])
    valid_ids = {kept["id"] for kept in dedup_map.values()}
    for kept in dedup_map.values():
        kept["crossLingualOf"] = sorted(
            t for t in canonical_links.get(kept["id"], ()) if t in valid_ids
        )

    # Sort: language (en first), then writtenForm
    words_list = sorted(
        dedup_map.values(),
        key=lambda w: (w["language"] != "en", w["writtenForm"].lower()),
    )

    print(
        f"  Raw Word nodes: {raw_count}  |  Deduped: {len(words_list)}  |  Merges: {merge_count}",
        file=sys.stderr,
    )

    # -- 6. Build driftTypes rollup ------------------------------------------
    drift_types: dict[str, dict] = {}
    for concept in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        in_scheme = g.value(concept, SKOS.inScheme)
        if in_scheme is None or str(in_scheme) != str(DRIFT.DriftTypeScheme):
            continue
        label = get_pref_label(g, concept)
        broader = g.value(concept, SKOS.broader)
        broader_label = get_pref_label(g, broader) if broader else None
        drift_types[str(concept)] = {
            "id": str(concept),
            "label": label,
            "broaderId": str(broader) if broader else None,
            "broaderLabel": broader_label,
        }

    # -- 7. Build aggregates --------------------------------------------------

    sense_conn: dict[str, str | None] = {s["id"]: s["connotation"] for s in sense_map.values()}

    # Pre-build CausalHypothesis index: drift_event_id -> list of hypothesis dicts
    causal_index: dict[str, list[dict]] = defaultdict(list)
    for hyp in sorted(g.subjects(RDF.type, DRIFT.CausalHypothesis), key=str):
        about_drift = g.value(hyp, DRIFT.aboutDrift)
        if about_drift is None:
            continue
        de_id = str(about_drift)

        trigger_node = g.value(hyp, DRIFT.proposedTrigger)
        trigger_label = None
        trigger_year = None
        trigger_category = None
        if trigger_node is not None:
            te = trigger_map.get(str(trigger_node))
            if te:
                trigger_label = te["label"]
                trigger_year = te["date"]
                trigger_category = te["category"]
            else:
                trigger_label = get_pref_label(g, trigger_node)

        evidence_labels = sorted(
            get_pref_label(g, ev)
            for ev in g.objects(hyp, DRIFT.evidenceType)
        )

        conf_lit = g.value(hyp, DRIFT.confidence)
        confidence = float(str(conf_lit)) if conf_lit is not None else None

        causal_index[de_id].append({
            "triggerLabel": trigger_label,
            "triggerYear": trigger_year,
            "category": trigger_category,
            "evidence": evidence_labels,
            "confidence": confidence,
        })

    for de_id in causal_index:
        causal_index[de_id].sort(key=lambda h: -(h["confidence"] or 0))

    # 7a. driftEventsFlat -- one compact record per drift event across all words
    drift_events_flat: list[dict] = []
    for word in words_list:
        for de in word["driftEvents"]:
            year_val = de["year"]
            from_conn = sense_conn.get(de["senseFromId"] or "", None) if de["senseFromId"] else None
            to_conn = sense_conn.get(de["senseToId"] or "", None) if de["senseToId"] else None
            causes = causal_index.get(de["id"], [])
            drift_events_flat.append({
                "word": word["writtenForm"],
                "lang": word["language"] or "?",
                "type": de["driftTypeLabel"] or "unknown",
                "year": year_val,
                "fromConn": from_conn,
                "toConn": to_conn,
                "hasTrigger": len(de["triggerIds"]) > 0,
                "causes": causes,
                "source": word["source"],
                "quality": word["quality"],
            })
    drift_events_flat.sort(key=lambda e: (e["year"] or 0, e["word"]))

    # 7b. byDecadeType -- stacked histogram [{decade, type, n}]
    from collections import Counter
    decade_type_counts: Counter = Counter()
    for fe in drift_events_flat:
        if fe["year"] is not None:
            decade = (fe["year"] // 10) * 10
            types_raw = fe["type"] or "unknown"
            for t in types_raw.split(","):
                t = t.strip()
                if t:
                    decade_type_counts[(decade, t)] += 1
    by_decade_type: list[dict] = [
        {"decade": k[0], "type": k[1], "n": v}
        for k, v in sorted(decade_type_counts.items())
    ]

    # 7c. triggerImpact -- per trigger event with wordCount and words
    trigger_word_map: dict[str, list[str]] = defaultdict(list)
    for word in words_list:
        word_form = word["writtenForm"]
        for de in word["driftEvents"]:
            for tid in de["triggerIds"]:
                if word_form not in trigger_word_map[tid]:
                    trigger_word_map[tid].append(word_form)

    trigger_impact: list[dict] = []
    for te_id, te in trigger_map.items():
        affected = trigger_word_map.get(te_id, [])
        trigger_impact.append({
            "trigger": te_id,
            "label": te["label"],
            "year": te["date"],
            "category": te["category"],
            "wordCount": len(affected),
            "words": sorted(affected),
        })
    trigger_impact.sort(key=lambda t: (-(t["wordCount"]), t["year"] or 0))

    # 7d. facets -- distinct values for filter UI
    all_langs = sorted({w["language"] or "?" for w in words_list})
    all_drift_types: list[str] = []
    seen_dt: set[str] = set()
    for fe in drift_events_flat:
        for t in (fe["type"] or "unknown").split(","):
            t = t.strip()
            if t and t not in seen_dt:
                seen_dt.add(t)
                all_drift_types.append(t)
    all_drift_types.sort()

    all_connotations = sorted({
        c
        for s in sense_map.values()
        for c in [s["connotation"]]
        if c
    })

    evidence_type_nodes: list[str] = []
    for concept in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        in_scheme = g.value(concept, SKOS.inScheme)
        if in_scheme is not None and str(in_scheme) == str(DRIFT.EvidenceTypeScheme):
            label = get_pref_label(g, concept)
            if label:
                evidence_type_nodes.append(label)
    evidence_type_nodes.sort()

    # Source and quality facets
    SOURCE_ORDER = ["Curated", "GfdS", "OWID", "DWUG", "SemEval", "Frequency"]
    QUALITY_ORDER = ["high", "benchmark", "detected"]
    all_sources_present = sorted(
        {w["source"] for w in words_list},
        key=lambda s: SOURCE_ORDER.index(s) if s in SOURCE_ORDER else 99,
    )
    all_qualities_present = sorted(
        {w["quality"] for w in words_list},
        key=lambda q: QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 99,
    )

    facets = {
        "language": all_langs,
        "driftType": all_drift_types,
        "connotation": all_connotations,
        "evidenceType": evidence_type_nodes,
        "source": all_sources_present,
        "quality": all_qualities_present,
    }

    # 7e. meta -- summary counts (deduped)
    total_drift_events = sum(len(w["driftEvents"]) for w in words_list)
    by_language: dict[str, int] = {}
    for w in words_list:
        lang = w["language"] or "?"
        by_language[lang] = by_language.get(lang, 0) + 1

    by_source: dict[str, int] = {}
    for w in words_list:
        by_source[w["source"]] = by_source.get(w["source"], 0) + 1

    by_quality: dict[str, int] = {}
    for w in words_list:
        by_quality[w["quality"]] = by_quality.get(w["quality"], 0) + 1

    meta = {
        "words": len(words_list),
        "rawWordNodes": raw_count,
        "mergedDuplicates": merge_count,
        "byLanguage": by_language,
        "bySource": by_source,
        "byQuality": by_quality,
        "driftEvents": total_drift_events,
        "triggers": len(trigger_map),
    }

    # -- 8. Assemble document -------------------------------------------------
    document = {
        "words": words_list,
        "triggers": sorted(trigger_map.values(), key=lambda t: t.get("date") or 0),
        "driftTypes": sorted(drift_types.values(), key=lambda dt: (dt.get("broaderLabel") or "", dt.get("label") or "")),
        "meta": meta,
        "driftEventsFlat": drift_events_flat,
        "byDecadeType": by_decade_type,
        "triggerImpact": trigger_impact,
        "facets": facets,
    }

    return document


def split_document(doc: dict) -> tuple[dict, dict]:
    """Split the full document into (core, detail).

    core   = everything for first paint, with LIGHT words (no heavy detail).
    detail = { wordId -> {senses, driftEvents, frequencyObservations, sources} }.

    This is a pure re-projection of `doc`: no field meaning changes, fields are
    only moved between files. Idempotent for a given input document.
    """
    light_words: list[dict] = []
    detail_map: dict[str, dict] = {}

    for w in doc["words"]:
        # Distinct drift-type labels for this word (split comma-joined labels).
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

        # Year span across senses (firstAttested + attested interval),
        # drift events (year + yearEnd), and frequency observations.
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


def main():
    print("Loading RDF graph...", file=sys.stderr)
    g = load_graph()
    print(f"  Triples loaded: {len(g)}", file=sys.stderr)

    print("Building export document...", file=sys.stderr)
    doc = build_document(g)

    words_count = len(doc["words"])
    triggers_count = len(doc["triggers"])
    print(f"  Words (deduped): {words_count}", file=sys.stderr)
    print(f"  Triggers: {triggers_count}", file=sys.stderr)
    print(f"  Drift types: {len(doc['driftTypes'])}", file=sys.stderr)
    print(f"  Source distribution: {doc['meta']['bySource']}", file=sys.stderr)
    print(f"  Quality distribution: {doc['meta']['byQuality']}", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=False)
    print(f"Written: {OUT_FILE}", file=sys.stderr)

    # Split into core (first paint) + detail (lazy) files.
    core, detail = split_document(doc)
    with open(CORE_FILE, "w", encoding="utf-8") as f:
        json.dump(core, f, ensure_ascii=False, indent=2, sort_keys=False)
    print(f"Written: {CORE_FILE}", file=sys.stderr)

    with open(DETAIL_FILE, "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2, sort_keys=False)
    print(f"Written: {DETAIL_FILE}", file=sys.stderr)

    full_sz = OUT_FILE.stat().st_size
    core_sz = CORE_FILE.stat().st_size
    detail_sz = DETAIL_FILE.stat().st_size
    print(
        f"  Sizes: graph.json={full_sz:,}B  "
        f"graph-core.json={core_sz:,}B  graph-detail.json={detail_sz:,}B",
        file=sys.stderr,
    )
    if full_sz:
        pct = 100.0 * (1 - core_sz / full_sz)
        print(
            f"  First-paint payload reduced {pct:.1f}% "
            f"(graph-core vs graph.json)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
