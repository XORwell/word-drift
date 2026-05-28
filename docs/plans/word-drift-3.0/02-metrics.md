# 02 — Metrics

> A metric that returns a number on a fragmented word and the same kind of number on a unanimous word is broken. Every metric here either returns a value with a stated range, or returns `null` with a stated reason. There is no third option.

This document specifies the ten quantitative metrics that 3.0 needs to support the competency questions, visualisations, and downstream analyses. Each metric is defined by intuition, formula, KG-input shape, SPARQL sketch, and failure modes. After the per-metric section, composition rules, confidence handling, time-travel semantics, and an explicit non-goals list.

Notation: $w$ is a word (IRI of an `ontolex:Word`), $t$ a timestamp, $g$ a `drift:Group`, $p$ a `drift:Platform`, $r$ a `drift:Region`, $S_w$ the finite set of `ontolex:Sense` IRIs attested for $w$. Every distribution below is computed from `drift:MeaningAttribution` records, each of which carries a sense, an optional group/platform/region/framing, a timestamp, and an evidence weight $\omega \in (0, 1]$ derived from corpus-occurrence count and source reliability (see ADR-0004).

For a word $w$ at time $t$ conditioned on a context variable $c$ (group, platform, region), the sense distribution is

$$P_w(s \mid c, t) = \frac{\sum_{a \in A_w(c, t)} \omega_a \cdot \mathbb{1}[\mathrm{sense}(a) = s]}{\sum_{a \in A_w(c, t)} \omega_a}$$

where $A_w(c, t)$ is the set of `MeaningAttribution` records for $w$ in context $c$ valid at $t$ under Trails KG time-travel. Marginalising over $c$ gives the unconditioned $P_w(s \mid t)$.

---

## 1. `semantic_entropy`

**Intuition.** How undecided is the word right now? A word with one dominant sense scores near zero. A word evenly split across many senses scores high.

**Formal definition.** Shannon entropy of the unconditioned sense distribution at $t$, in bits.

$$H(w, t) = -\sum_{s \in S_w} P_w(s \mid t) \log_2 P_w(s \mid t)$$

Range $[0, \log_2 |S_w|]$. Reported alongside $|S_w|$ so the upper bound is interpretable. Optional normalised variant $\tilde{H} = H / \log_2 |S_w| \in [0, 1]$ for cross-word comparison.

**Input.** `drift:MeaningAttribution` with `ontolex:isSenseOf` resolvable to $w$, timestamp $\le t$, evidence weight $\omega$. Group/platform irrelevant for this metric.

**SPARQL sketch.**
```sparql
PREFIX drift:   <https://w3id.org/word-drift/ontology#>
PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>

SELECT ?sense (SUM(?omega) AS ?mass) WHERE {
  ?attr a drift:MeaningAttribution ;
        drift:attributesSense ?sense ;
        drift:aboutWord ?w ;
        drift:evidenceWeight ?omega ;
        drift:validFrom ?from .
  OPTIONAL { ?attr drift:validUntil ?until . }
  FILTER(?w = <WORD_IRI>)
  FILTER(?from <= "T"^^xsd:dateTime)
  FILTER(!BOUND(?until) || ?until > "T"^^xsd:dateTime)
}
GROUP BY ?sense
```

**Failure modes.** With $|S_w| = 1$, $H = 0$ trivially; report `null` for normalised variant. Sparse evidence ($\sum \omega < \tau$, default $\tau = 5$) yields unstable estimates; report `null` and a `low_evidence` flag. Entropy ignores *which* senses split — a 50/50 split between near-synonyms looks identical to a 50/50 split between opposites. Pair with `semantic_polarization_score` when this matters.

---

## 2. `meaning_concentration`

**Intuition.** Inverse of entropy, biased toward the dominant sense: how much mass sits in the top sense?

**Formal definition.** Probability mass of the modal sense at $t$.

$$C(w, t) = \max_{s \in S_w} P_w(s \mid t) \in [0, 1]$$

A word with $C = 0.95$ is effectively monosemous in the corpus; $C = 0.34$ across three senses is a three-way tie.

**Input.** Same as `semantic_entropy`.

**SPARQL sketch.** Identical to entropy sketch; post-process by dividing each mass by the total and returning the maximum.

**Failure modes.** Insensitive to long-tail structure: $C(w_1, t) = 0.6$ over 2 senses and $C(w_2, t) = 0.6$ over 20 senses are clinically different. Always report alongside $|S_w|$. Cannot distinguish "one strong sense, one residual" from "one strong sense, five residuals". Use entropy as the companion.

---

## 3. `semantic_polarization_score`

**Intuition.** Are groups attributing *opposing* senses, not just *different* senses? High when two groups concentrate on senses that are themselves semantically far apart.

**Formal definition.** Let $G_w(t)$ be the set of groups with at least $n_{\min}$ attributions for $w$ at $t$ (default $n_{\min} = 3$). Let $d(s_i, s_j) \in [0, 1]$ be a pre-computed pairwise sense-distance (cosine distance on sense embeddings; see ADR-0003 when written). Define group-modal sense $s_g^\star = \arg\max_s P_w(s \mid g, t)$. Then

$$\mathrm{Pol}(w, t) = \frac{2}{|G_w(t)| (|G_w(t)| - 1)} \sum_{g < g'} d(s_g^\star, s_{g'}^\star) \cdot \min(C(w \mid g, t), C(w \mid g', t))$$

Range $[0, 1]$. The $\min(C, C)$ factor down-weights pairs where either group is itself uncertain — polarisation requires *confident disagreement*, not just disagreement.

**Input.** Per-group `MeaningAttribution` plus a sense-distance table (initially a stored predicate `drift:senseDistance` between `ontolex:Sense` pairs; later an embedding lookup).

**SPARQL sketch.**
```sparql
SELECT ?group ?sense (SUM(?omega) AS ?mass) WHERE {
  ?attr a drift:MeaningAttribution ;
        drift:aboutWord <WORD_IRI> ;
        drift:hasGroup ?group ;
        drift:attributesSense ?sense ;
        drift:evidenceWeight ?omega ;
        drift:validFrom ?from .
  FILTER(?from <= "T"^^xsd:dateTime)
}
GROUP BY ?group ?sense
```
Post-process: compute $s_g^\star$ per group, look up $d(\cdot, \cdot)$, aggregate.

**Failure modes.** Undefined when $|G_w(t)| < 2$ — report `null`, not `0`. A word can score `0` either because all groups agree (real consensus) or because the sense-distance table is missing entries (silent failure); guard with a coverage check on $d$ and report `partial_distance_table` when any pair is unknown. Sensitive to group taxonomy: splitting one group into two near-identical sub-groups inflates the denominator without changing semantics.

---

## 4. `semantic_fragmentation_index`

**Intuition.** How shattered is the word across the joint (group × platform × region) context space? Entropy over the *contexts* that distinguish senses, not over senses themselves.

**Formal definition.** Let $\Pi_w(t)$ be the partition of $A_w(\cdot, t)$ induced by grouping attributions whose modal sense agrees and whose context matches. For each block $B \in \Pi_w(t)$ let $\pi_B = \sum_{a \in B} \omega_a / \sum_a \omega_a$. Define

$$\mathrm{Frag}(w, t) = 1 - \sum_{B \in \Pi_w(t)} \pi_B^2 \quad \in [0, 1)$$

This is the Gini-Simpson diversity of the (context, sense) joint distribution. $\mathrm{Frag} = 0$ means one block holds all the mass (a unified word); $\mathrm{Frag} \to 1$ means the word fractures into many small same-sense same-context cells.

**Input.** `MeaningAttribution` with at least one of `drift:hasGroup`, `drift:fromPlatform`, `drift:inRegion` bound.

**SPARQL sketch.**
```sparql
SELECT ?group ?platform ?region ?sense (SUM(?omega) AS ?mass) WHERE {
  ?attr a drift:MeaningAttribution ;
        drift:aboutWord <WORD_IRI> ;
        drift:attributesSense ?sense ;
        drift:evidenceWeight ?omega ;
        drift:validFrom ?from .
  OPTIONAL { ?attr drift:hasGroup    ?group }
  OPTIONAL { ?attr drift:fromPlatform ?platform }
  OPTIONAL { ?attr drift:inRegion    ?region }
  FILTER(?from <= "T"^^xsd:dateTime)
}
GROUP BY ?group ?platform ?region ?sense
```

**Failure modes.** Highly sensitive to context-axis cardinality: introducing a new platform with 5 attributions and a new sense produces an immediate jump that reflects *coverage growth*, not real fragmentation. Always paired with the previous-period $\mathrm{Frag}$ value and the count of newly-attested contexts. If coverage grew by $> 20\%$ since the previous measurement, report fragmentation delta as `coverage_confounded`.

---

## 5. `drift_velocity`

**Intuition.** How fast is the unconditioned sense distribution moving right now?

**Formal definition.** Jensen-Shannon divergence per unit time between $P_w(\cdot \mid t)$ and $P_w(\cdot \mid t - \Delta)$, normalised to bits.

$$v(w, t; \Delta) = \frac{\mathrm{JSD}(P_w(\cdot \mid t) \,\|\, P_w(\cdot \mid t - \Delta))}{\Delta}$$

Units: bits per year (default $\Delta = 1$ year). Range $[0, 1/\Delta]$ since JSD is in $[0, 1]$ with $\log_2$ base. Choice of $\Delta$ is part of the query, not the metric.

**Input.** Two snapshots of `MeaningAttribution` mass at $t$ and $t - \Delta$. Use Trails time-travel for the second snapshot — no temporal field maths in SPARQL.

**SPARQL sketch.** Same as `semantic_entropy` sketch, executed twice against two `kg.at(t)` and `kg.at(t - delta)` time-travel handles. Post-process: compute both distributions, then JSD.

**Failure modes.** Sensitive to $\Delta$: too small and you measure annotation noise; too large and you smear real events. Default $\Delta = 1$ year for established corpora, 3 months for high-velocity platform corpora. When $\sum \omega$ at either snapshot is below $\tau$, return `null` with a `low_evidence_in_window` flag — do not interpolate.

---

## 6. `emotional_drift`

**Intuition.** Has the affective loading of the word moved, holding denotation roughly constant?

**Formal definition.** Let $v(w, t) \in [-1, 1]$ be the evidence-weighted mean valence over `drift:EmotionalFraming` records (positive = approving, negative = hostile). Let $a(w, t) \in [0, 1]$ be the weighted mean arousal (or `drift:loading`). Emotional drift over window $\Delta$ is

$$\Delta_e(w, t; \Delta) = \sqrt{(v(w, t) - v(w, t - \Delta))^2 + (a(w, t) - a(w, t - \Delta))^2}$$

Range $[0, \sqrt{5}]$ (since valence span is 2, arousal span is 1). Report as a pair $(\Delta v, \Delta a)$ as well as the scalar — sign of $\Delta v$ is load-bearing.

**Input.** `drift:EmotionalFraming` attached to `MeaningAttribution` via `drift:hasFraming`, with `drift:valence` and `drift:loading` literals and `drift:hasEvidence` (per ADR-0004, no framing without evidence).

**SPARQL sketch.**
```sparql
SELECT ?valence ?loading ?omega WHERE {
  ?attr a drift:MeaningAttribution ;
        drift:aboutWord <WORD_IRI> ;
        drift:hasFraming ?fr ;
        drift:evidenceWeight ?omega ;
        drift:validFrom ?from .
  ?fr drift:valence ?valence ;
      drift:loading ?loading .
  FILTER(?from <= "T"^^xsd:dateTime)
}
```
Run at $t$ and $t - \Delta$ via time-travel; compute weighted means; compute Euclidean distance in (valence, loading) space.

**Failure modes.** Affect annotation is high-variance — model-derived valence carries irreducible noise. Require $\ge n_{\min}^{\mathrm{aff}} = 10$ framing records per snapshot, else `null`. Conditioning on the modal sense (computing $\Delta_e$ holding sense constant) is the *interesting* query; the unconditioned version conflates denotation drift with affect drift and should be marked as such in output.

---

## 7. `group_divergence`

**Intuition.** How differently do two groups read the same word?

**Formal definition.** Jensen-Shannon divergence between group-conditioned sense distributions, in bits, in $[0, 1]$.

$$D(w, g_1, g_2, t) = \mathrm{JSD}(P_w(\cdot \mid g_1, t) \,\|\, P_w(\cdot \mid g_2, t))$$

For a set of groups, report the full pairwise matrix and the mean off-diagonal as a scalar summary.

**Input.** Per-group `MeaningAttribution` mass; the polarisation SPARQL sketch already returns the required shape.

**SPARQL sketch.** Same as `semantic_polarization_score`. Difference is purely in post-processing: JSD on the conditional distributions instead of distance between modal senses.

**Failure modes.** JSD on sparse distributions is biased upward; apply a Laplace smoothing prior of $\alpha = 0.5$ per sense before computing. Undefined for groups with zero attributions in the window — drop the row/column rather than returning `0`. Cannot tell *whether* groups disagree about the same sense or use disjoint sense inventories; pair with $|S_{w,g_1} \cap S_{w,g_2}|$ in the output dict.

---

## 8. `cross_platform_semantic_distance`

**Intuition.** Same idea as group divergence, but the context axis is `drift:Platform` instead of `drift:Group`.

**Formal definition.** Identical to `group_divergence` with $g \to p$:

$$D_p(w, p_1, p_2, t) = \mathrm{JSD}(P_w(\cdot \mid p_1, t) \,\|\, P_w(\cdot \mid p_2, t))$$

**Input.** `MeaningAttribution` with `drift:fromPlatform`. Per ADR planned for M6, `prov:wasDerivedFrom` must point to a corpus citation owned by that platform.

**SPARQL sketch.** As in group divergence with `?group` replaced by `?platform`.

**Failure modes.** Platform corpora differ in size and register independently of semantics. A platform with predominantly headline text will look distant from one with predominantly conversational text *for reasons orthogonal to drift*. Report register stratification alongside the distance when register annotations exist; do not silently aggregate across registers.

---

## 9. `historical_semantic_stability`

**Intuition.** A word that has been read the same way for decades scores high. A word that has moved, fractured, or re-fractured scores low.

**Formal definition.** Over a long window $W$ (default 30 years) sample $k$ equispaced timestamps $t_1, \ldots, t_k$ ($k = 30$). Let $D_{i,j} = \mathrm{JSD}(P_w(\cdot \mid t_i) \,\|\, P_w(\cdot \mid t_j))$. Stability is

$$\mathrm{Stab}(w, W) = 1 - \frac{2}{k(k-1)} \sum_{i < j} D_{i,j} \in [0, 1]$$

A flat-meaning word scores $1$; a word that has flipped twice scores well below $0.5$.

**Input.** Time-travel snapshots of `MeaningAttribution` at $k$ timestamps. Per the M2 fixture, real evidence is sparse before ~1990 for most words; flag accordingly.

**SPARQL sketch.** Run the entropy sketch $k$ times via `kg.at(t_i)`. Aggregate in Python.

**Failure modes. ** Coverage is the killer. Most words have rich evidence after 2000 and almost none before 1950; stability over $W = 100$ years is mostly a measure of corpus availability. Require $\ge 1$ attribution per sampled $t_i$ with sense diversity $\ge 1$, else mark $t_i$ as `extrapolated` and exclude from the sum (rescale denominator). Report effective $k$ in the output.

---

## 10. `historical_semantic_stability` companion — `cemetery_score`

(Lifted out of the master list because the vision doc names it.) Probability mass of the *historically dominant* sense $s^\dagger$ at present time $t$:

$$\mathrm{Cem}(w, t) = P_w(s^\dagger \mid t), \quad s^\dagger = \arg\max_s P_w(s \mid t_0)$$

with $t_0$ the earliest sampled snapshot. A word enters the cemetery when $\mathrm{Cem}(w, t) < 0.05$. Range $[0, 1]$.

**Failure mode.** $s^\dagger$ is the *dominant* historical sense, not the *original* sense — these differ for words whose earliest attestations are themselves sparse. Document the chosen $t_0$ per word.

---

## Composition rules

Cleanly composable:

- `group_divergence` × `cross_platform_semantic_distance` — orthogonal context axes; product or stack is meaningful as a 2-axis "where does this word fracture along".
- `semantic_polarization_score` × `meaning_concentration` per group — high polarisation with high per-group concentration is the *civil-war* configuration; high polarisation with low concentration is *each group is itself confused* (a different and rarer pattern).
- `drift_velocity` × `emotional_drift` — denotation and affect motion are independently meaningful; the pair is a 2D trajectory.

Do not compose:

- Do **not** multiply `semantic_entropy` and `semantic_polarization_score` — they overlap. Polarisation already encodes the spread part of entropy; their product double-counts.
- Do **not** average `semantic_fragmentation_index` across words to claim "the language is fragmenting"; coverage growth dominates real signal at corpus scale.
- Do **not** use `drift_velocity` and `historical_semantic_stability` as inverse of each other in the same report. Velocity is local-in-time; stability is global. They can both be high (recent change in a long-stable word) or both low (a word that has always been mildly noisy). Treating them as inverses obscures exactly the cases worth looking at.

## Confidence handling

Every metric reports `{point, ci_low, ci_high, n_evidence, flags}`. The point estimate uses the weighted distribution above; the 95% interval is derived from a non-parametric bootstrap over the underlying `MeaningAttribution` records, resampled with weights $\omega$, default $B = 1000$. The interval shrinks as $n_{\mathrm{evidence}}$ grows and as $\omega$ concentrates.

PROV-CRED-style propagation (per ADR planned for M3/M4) replaces the bootstrap-from-weights with proper credibility-interval propagation through the distribution arithmetic. The bootstrap is the M3 placeholder; the PROV-CRED hook is a metric-side `confidence_strategy` parameter so the call sites do not change when the propagation upgrades.

A metric that cannot compute a meaningful interval (e.g. polarisation on $|G_w| = 1$) returns `null` for `point` *and* `ci_*`, with a non-empty `flags` list naming the cause. Never `0`. Never silent `NaN`.

## Time-travel

All metrics are pure functions of a Trails KG handle at a timestamp. The signature is `metric(kg.at(t), word, **params) -> dict`. Implementations must never read `datetime.now()` internally. Snapshots used by velocity, emotional drift, and stability are obtained by repeated `kg.at(t_i)` calls; the metric layer is unaware that time-travel exists beyond the handle abstraction. This keeps the metrics testable against fixed fixtures and replayable for past timestamps.

## What we deliberately don't compute

- No `semantic_correctness` score. The KG does not encode which sense is right.
- No group-virtue ranking. `Group` is a descriptive label, never an evaluation.
- No "most-polarising-word-of-the-week" leaderboard. Polarisation is a property of a (word, time) pair queried by a user; surfacing a ranked stream invites optimisation against it.
- No aggregate "the German language is X% more fragmented than 2010" headline number. The composition rules forbid the averaging step that would produce it; if such a number appears in a UI we have a bug.
- No automated sentiment ground truth. Emotional metrics consume framings *with declared model + version*, never raw model output without provenance.
- No prediction. Metrics describe state. Forecasting drift is out of scope for 3.0 and likely all of 3.x.
