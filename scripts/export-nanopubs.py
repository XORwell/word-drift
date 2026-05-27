#!/usr/bin/env python3
"""
export-nanopubs.py — export each drift:CausalHypothesis as a nanopublication.

A causal hypothesis is a natural nanopublication: a single, individually-citable,
provenance-bearing assertion. We emit one nanopub per hypothesis as four named
graphs (the standard nanopub structure, Kuhn et al.):

  <np>        Head        : np:hasAssertion / hasProvenance / hasPublicationInfo
  <np_assert> Assertion   : the causal claim (hypothesis -> drift event, proposed
                            trigger, drift type) -- WHAT is claimed.
  <np_prov>   Provenance  : how the assertion was reached -- evidence type,
                            confidence, cited sources, curator attribution.
  <np_pubinfo>PublicationInfo : about the nanopub itself -- creator, created,
                            license.

Output: data/nanopub/word-drift-nanopubs.trig  (TriG = RDF with named graphs).
Validates as TriG. Read-only over examples/ + data/.

Usage: python scripts/export-nanopubs.py
"""
from __future__ import annotations

import glob
import pathlib
import warnings
from datetime import date

warnings.simplefilter("ignore")
import rdflib
from rdflib import Graph, Dataset, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD, DCTERMS

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = Namespace("https://w3id.org/word-drift/ontology#")
WDR = Namespace("https://w3id.org/word-drift/resource/")
NP = Namespace("http://www.nanopub.org/nschema#")
PROV = Namespace("http://www.w3.org/ns/prov#")
NPX = Namespace("http://purl.org/nanopub/x/")
BASE = "https://w3id.org/word-drift/np/"


def load() -> Graph:
    g = Graph()
    for f in glob.glob(str(ROOT / "examples/**/*.ttl"), recursive=True) + \
             glob.glob(str(ROOT / "data/**/*.ttl"), recursive=True):
        try:
            g.parse(f, format="turtle")
        except Exception:
            pass
    return g


def main() -> int:
    g = load()
    ds = Dataset()
    ds.bind("np", NP); ds.bind("npx", NPX); ds.bind("prov", PROV)
    ds.bind("drift", D); ds.bind("wdr", WDR); ds.bind("dct", DCTERMS)

    today = Literal(date.today().isoformat(), datatype=XSD.date)
    license_iri = URIRef("https://creativecommons.org/licenses/by/4.0/")
    creator = URIRef("https://orcid.org/0000-0000-0000-0000")  # placeholder ORCID

    n = 0
    for hyp in sorted(g.subjects(RDF.type, D.CausalHypothesis), key=str):
        local = str(hyp).split("/")[-1]
        np_uri = URIRef(BASE + local)
        assertion = URIRef(BASE + local + "#assertion")
        prov_g = URIRef(BASE + local + "#provenance")
        pub_g = URIRef(BASE + local + "#pubinfo")
        head = URIRef(BASE + local + "#Head")

        # Head graph: declares the nanopub parts
        h = ds.graph(head)
        h.add((np_uri, RDF.type, NP.Nanopublication))
        h.add((np_uri, NP.hasAssertion, assertion))
        h.add((np_uri, NP.hasProvenance, prov_g))
        h.add((np_uri, NP.hasPublicationInfo, pub_g))

        # Assertion graph: the causal claim
        a = ds.graph(assertion)
        drift = g.value(hyp, D.aboutDrift)
        trig = g.value(hyp, D.proposedTrigger)
        a.add((hyp, RDF.type, D.CausalHypothesis))
        if drift:
            a.add((hyp, D.aboutDrift, drift))
        if trig:
            a.add((hyp, D.proposedTrigger, trig))

        # Provenance graph: how the assertion was reached
        p = ds.graph(prov_g)
        for ev in g.objects(hyp, D.evidenceType):
            p.add((assertion, D.evidenceType, ev))
        conf = g.value(hyp, D.confidence)
        if conf is not None:
            p.add((assertion, D.confidence, conf))
        for src in g.objects(hyp, D.hasSource):
            p.add((assertion, PROV.wasDerivedFrom, src))
        att = g.value(hyp, PROV.wasAttributedTo)
        if att:
            p.add((assertion, PROV.wasAttributedTo, att))

        # Publication-info graph: about the nanopub itself
        pi = ds.graph(pub_g)
        pi.add((np_uri, PROV.generatedAtTime, today))
        pi.add((np_uri, DCTERMS.creator, creator))
        pi.add((np_uri, DCTERMS.license, license_iri))
        pi.add((np_uri, DCTERMS.rights, Literal("CC-BY 4.0", lang="en")))
        n += 1

    out = ROOT / "data" / "nanopub" / "word-drift-nanopubs.trig"
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(destination=str(out), format="trig")
    print(f"Wrote {n} nanopublications -> {out.relative_to(ROOT)}")

    # self-check: re-parse
    chk = Dataset()
    chk.parse(str(out), format="trig")
    print(f"  re-parsed OK: {len(list(chk.graphs()))} named graphs, {sum(len(gr) for gr in chk.graphs())} quads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
