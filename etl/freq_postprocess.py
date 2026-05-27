#!/usr/bin/env python3
"""Strip fallback-table causal hypotheses from Tier B (frequency) output.

The freq pipeline, when Wikidata was rate-limited, assigned every word a
trigger from a generic year -> event table (so the same event lands on every
word that shifted in that year). That is temporal coincidence dressed as
FrequencyCorrelation and would inject spurious causation into the graph
(see ADR 0004). We keep the genuinely reproducible detection data (words,
senses, drift events with driftYear, frequency observations, sources) and
remove the drift:CausalHypothesis + drift:TriggerEvent nodes. These words are
left "cause undetermined"; Tier C / curation proposes real per-word causes.

Idempotent: re-running on already-stripped files is a no-op.
"""
from __future__ import annotations

import glob
import sys

import rdflib
from rdflib.namespace import RDF

DRIFT = rdflib.Namespace("https://w3id.org/word-drift/ontology#")


def strip(path: str) -> tuple[int, int]:
    g = rdflib.Graph()
    g.parse(path, format="turtle")
    before = len(g)
    drop = set(g.subjects(RDF.type, DRIFT.CausalHypothesis)) | set(
        g.subjects(RDF.type, DRIFT.TriggerEvent)
    )
    for node in drop:
        for t in list(g.triples((node, None, None))):
            g.remove(t)
        for t in list(g.triples((None, None, node))):
            g.remove(t)
    g.serialize(destination=path, format="turtle")
    return len(drop), before - len(g)


def main() -> int:
    files = sorted(glob.glob("data/freq/*.ttl"))
    if not files:
        print("no data/freq/*.ttl found", file=sys.stderr)
        return 1
    total_nodes = total_triples = 0
    for f in files:
        nodes, triples = strip(f)
        total_nodes += nodes
        total_triples += triples
        print(f"  {f}: removed {nodes} hypothesis/trigger nodes, {triples} triples")
    print(f"stripped {total_nodes} nodes / {total_triples} triples across {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
