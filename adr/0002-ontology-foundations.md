# ADR 0002 — Ontology foundations and data strategy

**Status:** accepted · **Date:** 2026-05-23

## Context

We model words, senses-over-time, typed semantic-change events, and their
real-world triggers. We could invent everything, or reuse established vocabularies.

## Decision

**Reuse, align, add only the novel part.**

- **Lexical layer:** align to **OntoLex-Lemon** (`drift:Word ⊑ ontolex:LexicalEntry`,
  `drift:Sense ⊑ ontolex:LexicalSense`, reuse `ontolex:sense`).
- **Time:** **OWL-Time** intervals/instants for attestation and drift periods.
- **Provenance:** **PROV-O**; `drift:triggeredBy ⊑ prov:wasInfluencedBy`,
  `drift:hasSource ⊑ prov:wasDerivedFrom`. Source citation enforced by SHACL.
- **Taxonomies:** **SKOS** concept schemes for drift types, connotation, trigger
  categories.
- **Novel part we own:** `drift:DriftEvent` (reified, typed change) and the
  **causal layer** (`drift:TriggerEvent` + `drift:triggeredBy` + `drift:confidence`).

**Data strategy (two layers):**

1. **Benchmark backbone** — DWUG + SemEval-2020 Task 1 (DE+EN) for breadth and
   credibility; DWDS/Ngrams for frequency.
2. **Curated showcase set** — 20–30 hand-modelled, richly-triggered words for the
   demo and the causal contribution.

## Consequences

- External ontologies are referenced by IRI, not physically imported (matches
  CAN-KG); `validate.py` stays self-contained with `inference="rdfs"`.
- Causation is a *claim* (confidence + source), never asserted as fact — this is
  the defensible novelty and the eval's honest core.
- Sense granularity: adopt DWUG clusters for the backbone, curate for showcases
  (mapping to be documented in a later ADR).
