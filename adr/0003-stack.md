# ADR 0003 — Storage and query stack

**Status:** accepted · **Date:** 2026-05-23

## Context

Need to store, validate, query, and federate the graph; later visualise it and
serve a public tool. Workspace already has qlever (SPARQL MCP) and Trails (RML
ingest).

## Decision

- **Source of truth:** Turtle files in `ontology/`, `shapes/`, `examples/` —
  diffable, reviewable, git-native. `validate.py` (rdflib + pyshacl) is the gate.
- **Query/serve:** **qlever** for SPARQL at scale + **federation with Wikidata**
  (resolve `owl:sameAs` trigger links). Use the existing `mcp-server-qlever`.
- **Ingest:** **Trails RML** (`etl/rml/`) to lift DWUG/SemEval/DWDS tabular data
  into the `drift:` model; Python adapters in `etl/` for fetch + normalise.
- **Viz / public tool:** decided later; lean static-friendly (a lightweight static-site approach
  pattern), reading SPARQL results.

Rejected for now: Neon Postgres as primary store — the data is graph-native and
small; RDF + qlever gives federation for free. Revisit only if a write-heavy app
backend needs it (then Postgres + RDF export).

## Consequences

- Everything validates locally with two pip deps; no service required for the
  schema phase.
- RML mappings become the contract between messy source formats and the clean
  ontology.
