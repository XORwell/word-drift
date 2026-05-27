#!/usr/bin/env python3
"""
export-tables.py -- generate peer-review export artifacts into site/downloads/.

The headline artifact is the **claims ledger**: one row per drift:CausalHypothesis
with its word, sense shift, proposed trigger, evidence type(s), confidence, and
the cited source URLs -- so a reviewer can audit every causal claim, with its
evidence, in a spreadsheet.

Also emits tabular CSVs (words, drift events, triggers) and the full dataset in
three RDF serializations (Turtle, N-Triples, JSON-LD) for reuse.

Read-only over ontology/ + examples/ + data/. Output: site/downloads/.

Usage: python scripts/export-tables.py
"""
from __future__ import annotations

import csv
import glob
import pathlib
import warnings

warnings.simplefilter("ignore")
import rdflib
from rdflib import RDF, Literal, URIRef

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "downloads"
D = rdflib.Namespace("https://w3id.org/word-drift/ontology#")
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
RDFS = rdflib.RDFS
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
OWL = rdflib.OWL


def load(include_schema: bool) -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("drift", D); g.bind("wdr", "https://w3id.org/word-drift/resource/")
    pats = []
    if include_schema:
        pats += ["ontology/*.ttl"]
    pats += ["examples/**/*.ttl", "data/**/*.ttl"]
    for pat in pats:
        for f in glob.glob(str(ROOT / pat), recursive=True):
            try:
                g.parse(f, format="turtle")
            except Exception:
                pass
    return g


def lit(g, s, p, lang=None):
    if s is None:
        return None
    for o in g.objects(s, p):
        if lang is None or (isinstance(o, Literal) and o.language == lang):
            return str(o)
    for o in g.objects(s, p):
        return str(o)
    return None


def local(uri) -> str:
    return str(uri).rsplit("/", 1)[-1].rsplit("#", 1)[-1] if uri else ""


def claims_ledger(g: rdflib.Graph) -> list[dict]:
    rows = []
    for hyp in sorted(g.subjects(RDF.type, D.CausalHypothesis), key=str):
        drift = g.value(hyp, D.aboutDrift)
        trig = g.value(hyp, D.proposedTrigger)
        word = g.value(drift, D.affectsWord) if drift else None
        sense_from = g.value(drift, D.senseFrom) if drift else None
        sense_to = g.value(drift, D.senseTo) if drift else None
        dtypes = sorted(local(t) for t in g.objects(drift, D.driftType)) if drift else []
        dyear = g.value(drift, D.driftYear) if drift else None
        evid = sorted(local(e) for e in g.objects(hyp, D.evidenceType))
        conf = g.value(hyp, D.confidence)
        qid = g.value(trig, OWL.sameAs) if trig else None
        srcs = list(g.objects(hyp, D.hasSource))
        src_urls = [str(g.value(s, D.sourceURL)) for s in srcs if g.value(s, D.sourceURL)]
        src_titles = [lit(g, s, DCT.title) for s in srcs if lit(g, s, DCT.title)]
        rows.append({
            "hypothesis_id": local(hyp),
            "word": lit(g, word, D.writtenForm),
            "language": lit(g, word, D.language),
            "sense_from": lit(g, sense_from, D.gloss, "en"),
            "sense_to": lit(g, sense_to, D.gloss, "en"),
            "drift_type": "; ".join(dtypes),
            "drift_year": str(dyear) if dyear else "",
            "proposed_trigger": lit(g, trig, RDFS.label, "en") or lit(g, trig, RDFS.label),
            "trigger_date": str(g.value(trig, D.eventDate)) if trig and g.value(trig, D.eventDate) else "",
            "trigger_category": local(g.value(trig, D.triggerCategory)) if trig else "",
            "wikidata_qid": local(qid) if qid else "",
            "evidence_types": "; ".join(evid),
            "confidence": str(conf) if conf is not None else "",
            "source_urls": " | ".join(src_urls),
            "source_titles": " | ".join(t for t in src_titles if t),
            "attributed_to": local(g.value(hyp, PROV.wasAttributedTo)),
            "date": str(g.value(hyp, DCT.date)) if g.value(hyp, DCT.date) else "",
        })
    return rows


def words_table(g):
    rows = []
    for w in sorted(g.subjects(RDF.type, D.Word), key=str):
        rows.append({
            "word_id": local(w),
            "written_form": lit(g, w, D.writtenForm),
            "language": lit(g, w, D.language),
            "n_senses": len(list(g.objects(w, URIRef("http://www.w3.org/ns/lemon/ontolex#sense")))),
        })
    return rows


def triggers_table(g):
    rows = []
    for t in sorted(g.subjects(RDF.type, D.TriggerEvent), key=str):
        qid = g.value(t, OWL.sameAs)
        rows.append({
            "trigger_id": local(t),
            "label": lit(g, t, RDFS.label, "en") or lit(g, t, RDFS.label),
            "event_date": str(g.value(t, D.eventDate)) if g.value(t, D.eventDate) else "",
            "category": local(g.value(t, D.triggerCategory)),
            "wikidata_qid": local(qid) if qid else "",
        })
    return rows


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    g = load(include_schema=False)        # the dataset (no ontology schema)
    gfull = load(include_schema=True)     # dataset + schema, for the RDF dumps

    ledger = claims_ledger(g)
    write_csv(OUT / "claims-ledger.csv", ledger)
    write_csv(OUT / "words.csv", words_table(g))
    write_csv(OUT / "triggers.csv", triggers_table(g))

    # RDF dumps (dataset + schema) in three serializations
    gfull.serialize(destination=str(OUT / "word-drift.ttl"), format="turtle")
    gfull.serialize(destination=str(OUT / "word-drift.nt"), format="nt")
    gfull.serialize(destination=str(OUT / "word-drift.jsonld"), format="json-ld", auto_compact=True)

    print(f"Claims ledger: {len(ledger)} causal hypotheses -> site/downloads/claims-ledger.csv")
    print(f"words.csv: {len(words_table(g))} | triggers.csv: {len(triggers_table(g))}")
    print(f"RDF dumps: word-drift.ttl / .nt / .jsonld ({len(gfull)} triples incl. schema)")
    # quick integrity: every ledger row should have at least one source
    no_src = [r['hypothesis_id'] for r in ledger if not r['source_urls'] and not r['source_titles']]
    print(f"Ledger rows without a source: {len(no_src)}" + (f" -> {no_src[:5]}" if no_src else " (all sourced)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
