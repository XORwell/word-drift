#!/usr/bin/env python3
"""
build_items.py — extract every curated causal hypothesis with its context into a
flat annotation item list (eval/iaa/items.json).

One item = one drift:CausalHypothesis, with the information an annotator needs to
judge "does this trigger plausibly explain this drift?": word, language, the
prior and new sense gloss, drift type, the proposed trigger label + description +
date, the curator's evidence type(s) and confidence, and the cited source URLs.

Read-only over examples/. Output: eval/iaa/items.json.
"""
from __future__ import annotations

import glob
import json
import pathlib
import warnings

warnings.simplefilter("ignore")
import rdflib

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = rdflib.Namespace("https://w3id.org/word-drift/ontology#")
RDFS = rdflib.RDFS
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
RDF = rdflib.RDF


def lit(g, s, p, lang=None):
    for o in g.objects(s, p):
        if lang is None or (isinstance(o, rdflib.Literal) and o.language == lang):
            return str(o)
    # fallback: any value
    for o in g.objects(s, p):
        return str(o)
    return None


def main() -> int:
    g = rdflib.Graph()
    for f in glob.glob(str(ROOT / "examples/**/*.ttl"), recursive=True):
        try:
            g.parse(f, format="turtle")
        except Exception:
            pass

    items = []
    for hyp in sorted(g.subjects(RDF.type, D.CausalHypothesis), key=str):
        drift = g.value(hyp, D.aboutDrift)
        trig = g.value(hyp, D.proposedTrigger)
        if drift is None or trig is None:
            continue
        word = g.value(drift, D.affectsWord)
        sense_from = g.value(drift, D.senseFrom)
        sense_to = g.value(drift, D.senseTo)
        drift_type = g.value(drift, D.driftType)

        evidence = sorted(str(e).split("#")[-1] for e in g.objects(hyp, D.evidenceType))
        conf = g.value(hyp, D.confidence)
        sources = []
        for src in g.objects(hyp, D.hasSource):
            url = g.value(src, D.sourceURL)
            title = lit(g, src, DCT.title)
            sources.append(url and str(url) or title or str(src))

        items.append({
            "hyp_id": str(hyp).split("/")[-1],
            "word": lit(g, word, D.writtenForm) if word else None,
            "language": lit(g, word, D.language) if word else None,
            "sense_from": lit(g, sense_from, D.gloss, "en") if sense_from else None,
            "sense_to": lit(g, sense_to, D.gloss, "en") if sense_to else None,
            "drift_type": str(drift_type).split("#")[-1] if drift_type else None,
            "trigger_label": lit(g, trig, RDFS.label, "en") or lit(g, trig, RDFS.label),
            "trigger_desc": lit(g, trig, DCT.description, "en") or lit(g, trig, DCT.description),
            "trigger_date": str(g.value(trig, D.eventDate)) if g.value(trig, D.eventDate) else None,
            "evidence_type": evidence,
            "curator_confidence": float(str(conf)) if conf is not None else None,
            "sources": sources,
        })

    out = ROOT / "eval" / "iaa" / "items.json"
    out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} annotation items -> {out.relative_to(ROOT)}")
    # quick strata report
    from collections import Counter
    print("  by language:", dict(Counter(i["language"] for i in items)))
    print("  by strongest evidence:", dict(Counter(
        (i["evidence_type"][-1] if i["evidence_type"] else "none") for i in items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
