# ADR 0003 — Platform, corpus-context, and register as three classes

**Status:** Proposed

## Context

"Context" in `00-vision.md §2.3` covers at least three things that are routinely conflated:

- **Platform.** The technical and institutional substrate: Reddit, Wikipedia, Bundestag, *FAZ*, a personal blog hoster. Long-lived, identifiable, often with its own ToS and norms.
- **Corpus context.** A nameable sub-region of a platform that hosts language: a subreddit, a Wikipedia language edition + namespace, a Bundestag session, a particular newspaper's opinion page. One platform hosts many corpus contexts.
- **Register.** A stylistic / pragmatic stratum: casual vs. formal, spoken vs. written, public-facing vs. in-group, ironic vs. sincere. Registers exist across platforms; the same Reddit thread can mix registers within itself.

Treating these as one "context" string makes cross-platform queries ("compare register-matched usage across platforms") collapse into hand-rolled substring matching, and makes platform-aware SHACL ("a Reddit attribution must cite a Reddit-belonging corpus") inexpressible.

## Decision

Three first-class classes in the 3.0 ontology, in module `09-platform-context.ttl`:

- `drift:Platform` — Reddit, Wikipedia, Bundestag, an individual newspaper, a single blog host. Carries a canonical IRI and a stable label.
- `drift:CorpusContext` — a sub-region of a platform; `prov:wasInfluencedBy` a `Platform`. r/de, *de.wikipedia.org*, the Bundestag session of 2021-03-04, the opinion page of *Die Zeit*.
- `drift:Register` — `skos:Concept` instances in a `drift:RegisterScheme`: casual, formal, spoken, written, public-facing, in-group, ironic, sincere. SKOS rather than OWL classes because the inventory will grow and overlap.

A `drift:MeaningAttribution` may carry zero or one `drift:onPlatform` (some attributions are platform-agnostic, e.g. dictionary), zero or one `drift:inCorpusContext`, and any number of `drift:hasRegister` annotations. SHACL requires that if `drift:inCorpusContext` is set, then the linked `CorpusContext` resolves to a `Platform` consistent with `drift:onPlatform` (or `drift:onPlatform` is unset).

## Consequences

- Cross-platform queries become structural ("all attributions with `drift:onPlatform drift:Reddit`"), not lexical.
- The same `Register` ("ironic, in-group") can be queried across Platforms without per-platform string handling.
- M6 (platform divergence) and M7 (emotional framing) both get a stable axis to compute against.
- Three classes are slightly more ontology than the smallest viable model. The cost is paid once at modelling time and pays back at every cross-platform query.

## Alternatives considered

- **One "context" string.** Rejected: collapses three orthogonal axes, kills cross-platform queries.
- **Two classes (Platform + Register), CorpusContext as a string property of attribution.** Rejected because SHACL cannot then enforce that a "subreddit" string corresponds to the Reddit Platform. Once we want that check — and M6 requires it — CorpusContext has to be a class anyway.
- **CorpusContext as `prov:Collection`.** Considered. Compatible, and we will likely declare `drift:CorpusContext rdfs:subClassOf prov:Collection`. Not an alternative so much as a refinement.
