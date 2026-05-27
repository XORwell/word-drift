# Strict verifiability criteria for curated entries

The user requires that the curated set contain only **verifiable** claims. Many
Wave-3 entries (contemporary slang, gradual shifts) sound plausible but rest on
invented dates or unsupported folk etymology (e.g. `based` had
`firstAttested 1980` for a slur sense with no source backing that date). Apply
this bar to every assigned word.

## What to check, per word

For each `examples/<word>.ttl`, FETCH its cited `drift:sourceURL`s (and, if useful,
the obvious authority for the word) and check whether the sources actually
substantiate:

1. **The sense shift** — does an authority (DWDS, OED, etymonline, Wiktionary,
   Wikipedia, or a named scholarly work) attest the old sense AND the new sense?
2. **The trigger / cause** — does a source connect the shift to the proposed
   trigger event (for eponyms: the namesake; for events: the event)?
3. **The dates** — is each `xsd:gYear` (firstAttested, eventDate, drift interval)
   actually supported, or is it a suspiciously round/invented number?

## Verdict and action (lean toward FIX over delete, but be strict)

- **KEEP (verified):** sources resolve and substantiate the sense shift AND the
  trigger. Leave as is.
- **FIX (verifiable core, bad details):** the sense shift + trigger are
  verifiable, but a date is unsupported/invented or a claim is over-precise.
  Then: replace the invented `firstAttested`/`eventDate` with a value the source
  supports, or if the source gives no year, WIDEN to a defensible century/decade
  or remove that single date triple (keep the entry valid per SHACL). Downgrade
  `drift:confidence` and/or `drift:evidenceType` to match what the source really
  supports (e.g. Speculative if it is only plausible). Fix or replace a dead/wrong
  source URL with a working authority. Tighten the gloss/description to what is
  attested.
- **REMOVE (unverifiable):** if even the core sense shift or the trigger cannot
  be supported from any authority (pure folk etymology, dead sources with no
  replacement, a cause no source connects), DELETE the whole `examples/<word>.ttl`
  file. A wrong/unverifiable entry is worse than a smaller corpus.

## Hard rules

- Honour SHACL: any file you KEEP or FIX must still validate (every DriftEvent has
  >=1 source; every CausalHypothesis has evidenceType + confidence + source +
  proposedTrigger + aboutDrift; speculative-only confidence < 0.66). Run
  `python validate.py` at the end and fix any violation you introduced.
- 4-digit zero-padded gYears; NO em-dashes; keep Turtle valid.
- Do NOT invent a date or a source to "save" an entry. If you cannot verify it,
  FIX it down to what is verifiable, or REMOVE it. Honesty over coverage.
- Only touch the files in YOUR assigned chunk. Do not touch ontology/, shapes/,
  viz/, site/, paper/, data/, scripts/, validate.py, or another chunk's files.

## Output

Write a report fragment `data/reports/verify-chunk<N>.md` with one row per word:
`word | verdict (KEEP/FIX/REMOVE) | what the sources did/didn't support | action taken`.
At the end report counts (kept / fixed / removed) and the removed list with reasons.
