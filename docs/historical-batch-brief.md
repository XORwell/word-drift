# Historical batch — shared curator brief

Goal: add **trigger-driven historical words** to fill the pre-2000 / pre-1950 /
pre-1900 gap. Every word must have a **crisply datable causal trigger** (an
eponym, an event, an institution). If a word's trigger is NOT cleanly datable
and sourceable, **drop it** — do not invent dates or causes (ADR 0004).

## File format

One word = one file `examples/<slug>.ttl`. Copy the structure of
`examples/pfaffe.ttl` **exactly** (prefixes, block order, comment header).
Blocks: Word -> Sense(s) -> TriggerEvent -> DriftEvent -> CausalHypothesis ->
(reuse `wdr:curator`) -> Source(s).

IRI naming: `wdr:word-<slug>`, `wdr:sense-<slug>-<tag>`,
`wdr:trigger-<slug>-<tag>`, `wdr:drift-<slug>-<tag>`, `wdr:hyp-<slug>-<tag>`,
`wdr:src-<slug>-<tag>`. Slugs are lowercase ASCII; for German use ASCII
transliteration in the slug (ae/oe/ue/ss) but keep correct spelling in
`drift:writtenForm` and `rdfs:label`.

## Hard rules

- **gYear literals MUST be 4 digits**, zero-padded: `"0800"^^xsd:gYear`, never
  `"800"`. For BC dates use a clearly-labelled interval and pick the nearest
  sensible 4-digit anchor in the prose; do not emit negative gYears.
- **No em-dashes** anywhere. Use comma/semicolon/parentheses/period.
- German text in `@de` literals: transliterate umlauts (ae/oe/ue/ss) to match the
  existing examples (see pfaffe.ttl: "veraechlich", "Berufsbezeichnung").
- Every `drift:Source` needs a real, resolvable `drift:sourceURL` (DWDS,
  de.wiktionary.org, en.wiktionary.org, etymonline.com, de/en.wikipedia.org).
  Use 1-2 sources per word. Only cite pages you are confident exist.
- Reuse the single shared `wdr:curator a prov:Agent` (define it once per file,
  same as pfaffe.ttl).

## Controlled vocabularies (use ONLY these)

- `drift:driftType`  : Pejoration, Amelioration, Broadening, Narrowing,
  Metaphorization, Metonymization, Reversal, Reappropriation
- `drift:connotation`: Positive, Neutral, Negative
- `drift:triggerCategory` (ONLY these 6): Political, Pandemic, Technology,
  Cultural, Media, Commercial. Map: religion/art/intellectual -> Cultural;
  war/revolution/state -> Political; science/engineering/invention -> Technology;
  disease/quarantine -> Pandemic; press/song/broadcast -> Media; brand/eponymous
  product -> Commercial.
- `drift:evidenceType` (ladder, weakest->strongest): Speculative <
  FrequencyCorrelation < ChangeSignalAlignment < LexicographicNote <
  ScholarlyAttestation. For well-documented eponyms/events backed by a
  dictionary entry use **LexicographicNote**; if backed by a named scholarly
  account use **ScholarlyAttestation**.
- `drift:confidence`: a float 0.5-0.9. Be honest: crisp eponym = 0.8-0.9; a
  plausible but debated link = 0.6-0.7.

## CausalHypothesis (ADR 0004)

Causation is never asserted as a shortcut. Each word's causal claim is a
reified `drift:CausalHypothesis` with: `drift:aboutDrift`, `drift:proposedTrigger`,
`drift:evidenceType`, `drift:confidence`, `drift:hasSource`,
`prov:wasAttributedTo wdr:curator`, `dct:date "2026-05-23"^^xsd:date`.

## After writing your files

Run `python validate.py 2>&1 | tail -5` from the project root and confirm it
prints "All checks passed." Fix any SHACL violation in YOUR files before
finishing. Do NOT edit ontology/, shapes/, validate.py, data/, viz/, or any
example file outside your assigned word list.
