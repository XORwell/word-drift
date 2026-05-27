# ADR 0004 — Causation as evidenced hypothesis, not asserted fact

**Status:** accepted · **Date:** 2026-05-23 · **Supersedes part of:** 0002 (causal layer)

## Context

The novel contribution of WORD-DRIFT is linking a semantic shift to the
real-world event that reframed the word. v0.1/v0.2 modelled this as
`drift:DriftEvent drift:triggeredBy drift:TriggerEvent` with a single
`drift:confidence` on the drift event. Two problems make this academically
fragile and invite the question "was your event source even trustworthy?":

1. **Causation is asserted, not claimed.** No single event can be *proven* to
   cause a meaning shift; language change is overdetermined. The word
   "triggered" overclaims and is the obvious target for a reviewer.
2. **Two different claims are conflated.** "The event existed and is dated" (an
   external fact) and "the event reframed the word" (our interpretation) have
   completely different provenance needs but share one node + one confidence.

## Decision

Adopt an **evidenced-hypothesis** model with strict provenance separation.

### 1. Separate the two claims

- **Event existence / date:** never asserted by us. A `drift:TriggerEvent` is
  *referenced* from an external, provenance-bearing source (Wikidata via
  `owl:sameAs`; EventKG as the scaling source, see below). Our `drift:eventDate`
  is a convenience copy that the federated audit query cross-checks against the
  source (P585/P571). The trust question is delegated to a citable resource.
- **Causal claim:** ours, but framed as a *hypothesis*, reified, graded, and
  evidence-bearing.

### 2. Reify the causal claim as a hypothesis

Canonical class `drift:CausalHypothesis` (n-ary reification, like CAN-KG's
`ConcentrationStatement`):

```
drift:CausalHypothesis
  drift:aboutDrift     -> drift:DriftEvent
  drift:proposedTrigger -> drift:TriggerEvent
  drift:evidenceType   -> SKOS concept (see ladder)
  drift:confidence     -> xsd:decimal [0.0, 1.0]
  drift:hasSource      -> drift:Source   (evidence FOR the link)
  prov:wasAttributedTo -> agent who proposes the hypothesis
  dct:date             -> when proposed
```

Multiple competing hypotheses per drift event are allowed and expected.
There is **no `drift:triggeredBy` shortcut**: during the fresh build we keep one
canonical model rather than two paths. Every causal statement is a hypothesis.
Queries join `Word -> DriftEvent -> CausalHypothesis -> TriggerEvent`.

### 3. Evidence ladder (mandatory, typed)

A hypothesis is "supported" only if it carries at least one **non-speculative**
evidence type. SKOS scheme `drift:EvidenceTypeScheme`, ordered weak to strong:

- `drift:Speculative` — temporal coincidence asserted by us only. Allowed but
  flagged; never sufficient alone for "supported".
- `drift:FrequencyCorrelation` — the word's frequency curve (our
  `drift:FrequencyObservation` data) spikes at the event. **Reproducible** from a
  public corpus, independent of our judgement.
- `drift:ChangeSignalAlignment` — the diachronic usage-graph / embedding change
  signal from DWUG/SemEval aligns with the event date. Strongest reproducible
  evidence because it is the field's own accepted change measure.
- `drift:LexicographicNote` — a dictionary etymology note states the link.
  **Attributed**, not ours.
- `drift:ScholarlyAttestation` — a peer-reviewed study states the link.
  Strongest attributed evidence.

Rule (SHACL): every `drift:CausalHypothesis` has `drift:evidenceType` +
`drift:confidence` in [0,1] + at least one `drift:hasSource`.

### 4. Source typing + reliability

`drift:Source` gains subclasses: `drift:ScholarlyStudy`, `drift:Dictionary`,
`drift:Encyclopedia`, `drift:NewsArticle`, `drift:Dataset`, plus an optional
`drift:reliabilityTier` (1 highest). Causal hypotheses should prefer secondary /
scholarly sources; tertiary sources (Wikipedia/Wikidata) back event *existence*,
not the causal claim.

### 5. Provenance standard

PROV-O now. **Nanopublications** (assertion / provenance / pubinfo named graphs)
as the FAIR endgame so each hypothesis is independently citable and
machine-auditable. Releases get a **Zenodo DOI** so every claim pins to a
versioned graph state.

## Consequences

- Reviewer question "was the event source trustworthy?" is answered structurally:
  we do not assert events (we reference EventKG/Wikidata), and causation is a
  typed, graded, individually-cited hypothesis with reproducible-or-attributed
  evidence. Trust shifts from "believe us" to "audit the chain".
- `validate.py` stays green: shapes require the hypothesis invariants; the old
  `drift:confidence`-on-DriftEvent rule is dropped and `drift:triggeredBy` is
  removed entirely. `drift:confidence` now has `rdfs:domain drift:CausalHypothesis`,
  so any stray confidence on a drift event is (correctly) flagged by SHACL.
- Migration in v0.3: all curated examples gain `drift:CausalHypothesis` nodes
  with typed evidence; purely language-internal shifts (no trigger) carry no
  hypothesis and no confidence. Bulk detection data (data/real) carries a
  detection score, not a causal confidence (renamed accordingly).
- Queries `triggers.rq` and the federated `reframed-by-event.rq` join through
  the hypothesis; `causal-evidence.rq` is the audit view (claim + evidence type
  + confidence).

## Deferred (documented, not built in v0.3)

- **EventKG ingest** for trigger events with per-statement provenance (the proper
  scaling path for the event layer).
- **ChangeSignalAlignment** computed from DWUG/SemEval graded-change scores.
- **GDELT** media-attention curves as reproducible evidence for media-driven
  terms (woke, viral, spam).
- **Nanopublication export** + **Zenodo DOI** release pipeline.
