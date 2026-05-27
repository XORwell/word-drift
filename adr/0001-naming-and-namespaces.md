# ADR 0001 — Naming and namespaces

**Status:** accepted · **Date:** 2026-05-23

## Context

New KG project on lexical semantic change. Needs a descriptive (non-branded)
name in line with the workspace's CAN-KG pattern, and an RDF namespace that does
not collide with the vocabularies it federates against.

## Decision

- **Project / repo name:** `word-drift` (working name). Field terms recorded:
  *Lexical Semantic Change (LSC)* / *Bedeutungswandel*. No invented brand.
- **Ontology namespace:** `drift:` = `https://w3id.org/word-drift/ontology#`
- **Resource namespace:** `wdr:` = `https://w3id.org/word-drift/resource/`
- **Reserved, not used:** `wd:` / `wdt:` — these belong to **Wikidata**, which we
  federate with via `owl:sameAs`. Using `drift:` avoids the clash entirely.

## Consequences

- `w3id.org` base IRIs are aspirational; they need not resolve for validation.
  Register a w3id redirect before any public publication.
- App/product brand deferred (cf. CAN-KG ADR 0011) — descriptive name is enough
  for the schema + paper phase.
