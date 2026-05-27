# WORD-DRIFT — causal-hypothesis annotation guidelines (codebook)

These guidelines govern the inter-annotator agreement (IAA) study on the causal
hypotheses. They are used by both the human annotation round and the LLM
reliability pilot, so the two are directly comparable.

## What you are judging

WORD-DRIFT records, for many words, a **drift event** (a documented shift in
meaning) and a **proposed trigger** (a datable real-world event or origin the
curator believes is associated with that shift). Under ADR 0004 the project never
*asserts* a cause; it records a graded, sourced **hypothesis**. Your job is to
independently judge how good that hypothesis is.

You will see, per item: the word and its language, the prior sense and the new
sense, the drift type, the proposed trigger (label, description, date), and the
cited sources. You do **not** see the curator's confidence value (it must not
anchor you).

## Primary task — plausibility (binary)

> **Q1. Does the proposed trigger plausibly explain this shift in meaning?**
> Answer **yes** or **no**.

- **yes** = a reasonable, informed reader would accept the trigger as a credible
  cause or origin of the shift, given the sources. It need not be the *only*
  cause, and you need not be certain; "plausible on balance" is enough.
- **no** = the link is far-fetched, anachronistic (trigger postdates the shift),
  circular, or the trigger is too generic to explain *this specific* shift
  (e.g. "general language change").

Decision aids:
- Check the **dates**: a trigger dated after the new sense appears cannot cause it.
- Distinguish **origin** (eponyms/toponyms: the word came from the name/place) from
  **reframing** (an event changed an existing word's connotation). Both count as
  "explains" if the mechanism fits the drift type.
- Generic, undated, or tautological triggers → **no**.

## Secondary task — evidence tier appropriateness (optional, ordinal)

> **Q2. Is the strongest evidence tier the curator could honestly claim:**
> Speculative (1) < FrequencyCorrelation (2) < ChangeSignalAlignment (3) <
> LexicographicNote (4) < ScholarlyAttestation (5)?

Give the tier **you** think is justified by the sources shown (1-5). This lets us
measure agreement on evidence strength, not just plausibility.

- **Speculative**: a guess, no corroboration.
- **FrequencyCorrelation**: the shift coincides with a frequency change in a corpus.
- **ChangeSignalAlignment**: a benchmark (DWUG/SemEval) graded change score aligns.
- **LexicographicNote**: a dictionary/etymological note states the connection.
- **ScholarlyAttestation**: a named scholarly account argues the connection.

## Rules to keep annotators independent and comparable

1. Judge each item on its own; do not compare items to each other.
2. Use only the information shown plus your general knowledge. Do not look up the
   curator's confidence.
3. When genuinely undecided on Q1, choose the answer you lean toward; do not
   abstain (a forced binary keeps kappa interpretable).
4. Record a one-line rationale for any **no**.

## How agreement is computed

- **Annotator 1 (curator):** the curator's own confidence, binarised at
  `>= 0.66 -> yes`, `< 0.66 -> no` (documented threshold; the 0.5-0.9 curator
  scale puts the natural "plausible" cut at two thirds).
- **Annotators 2..k:** independent human raters (real round) or independent LLM
  runs (pilot), each producing a yes/no for Q1 and a tier for Q2.
- **Metrics:** pairwise Cohen's kappa on Q1; Krippendorff's alpha (nominal for
  Q1, ordinal for Q2) across all annotators; raw percent agreement.

The LLM pilot is a **reliability probe, not ground truth**. LLM raters can share
correlated blind spots, so high LLM-LLM agreement is weak evidence; the
curator-vs-LLM number is the informative one, and the human round is the
authoritative measure.
