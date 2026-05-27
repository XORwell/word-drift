# Contributing to WORD-DRIFT

Thanks for your interest. WORD-DRIFT is a small research project;
contributions are welcome but a few rules keep the schema honest and
the test suite green.

## What kind of contributions

| Type | Bar | Example |
|------|-----|---------|
| **New curated word** (`examples/`) | medium -- must cite a source + use correct namespaces | `examples/nice.ttl` (amelioration, EN) |
| **Schema fix** (typo, wrong domain/range, missing label) | low -- open a PR | corrected `drift:driftYear` range |
| **New SHACL constraint** | medium -- must include a passing AND a failing fixture | `drift:confidenceRange` shape |
| **New SPARQL query** | low -- must run via `validate.py` cleanly | `queries/broadening.rq` |
| **New ETL adapter** | medium -- must be polite to upstream, emit `drift:hasSource` | `etl/google_ngrams.py` |
| **New ontology module** | high -- requires an ADR + maintainer review | a `drift:SociolinguisticContext` module |

## Adding a new example word

The pattern is one file: `examples/<word>.ttl` (use `-de` suffix for German
words that would clash, e.g. `gift-de.ttl`).

Minimal valid structure:

```turtle
@prefix drift: <https://w3id.org/word-drift/ontology#> .
@prefix wdr:   <https://w3id.org/word-drift/resource/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix dct:   <http://purl.org/dc/terms/> .

wdr:Word_<word> a drift:Word ;
    drift:lemma "<word>"@<lang> ;
    drift:language "<lang>" .

wdr:Sense_<word>_1 a drift:Sense ;
    drift:word wdr:Word_<word> ;
    drift:definition "..."@<lang> ;
    drift:connotation drift:Positive ;   # or Neutral / Negative
    drift:firstAttested "YYYY"^^xsd:gYear .

wdr:DriftEvent_<word>_1 a drift:DriftEvent ;
    drift:affectsWord wdr:Word_<word> ;
    drift:senseFrom wdr:Sense_<word>_1 ;
    drift:senseTo   wdr:Sense_<word>_2 ;
    drift:driftType drift:Pejoration ;   # pick from taxonomy
    drift:driftYear "YYYY"^^xsd:gYear ;
    drift:hasSource [ a drift:Source ;
        dct:title "..." ;
        dct:source <https://...> ] .
```

If you have a defensible trigger, add:

```turtle
wdr:DriftEvent_<word>_1
    drift:triggeredBy wdr:Trigger_<event> ;
    drift:confidence  "0.8"^^xsd:decimal .

wdr:Trigger_<event> a drift:TriggerEvent ;
    drift:eventLabel "..."@en ;
    drift:eventYear  "YYYY"^^xsd:gYear ;
    drift:hasSource  [ a drift:Source ; dct:title "..." ; dct:source <https://...> ] .
```

## Invariants (enforced by SHACL and tests)

1. **Every drift event cites a source.** `drift:hasSource` on every
   `drift:DriftEvent` is a SHACL requirement. A Wikipedia article or a
   published dictionary entry is sufficient.

2. **Every asserted trigger carries confidence.** If you write
   `drift:triggeredBy`, you must also write `drift:confidence` (0.0 to 1.0).
   Speculative links go at 0.4 or below; well-attested causal connections
   at 0.8 or above.

3. **Namespaces: `drift:` and `wdr:` only for our data.** Never use `wd:` for
   WORD-DRIFT resources -- that prefix belongs to Wikidata. Wikidata items are
   linked via `owl:sameAs` from `wdr:Trigger_*` nodes.

4. **No em-dashes** in any prose, comments, or labels. Use a comma, semicolon,
   or parentheses instead.

5. **English for code, comments, commits, and docs.** German lemmas are fine in
   `drift:lemma` values (with `@de` language tag).

## Workflow

1. Fork or push a branch on the upstream repo
2. `pip install rdflib pyshacl pytest`
3. Run `python validate.py` before any changes (baseline)
4. Make your change
5. Run the green gate:
   ```bash
   python validate.py   # SHACL + SPARQL
   make test            # 38 pytest tests
   ```
   Both must exit 0.
6. Open a PR with:
   - what word/feature you added
   - one sentence explaining why (cite a source, link an ADR)
   - `validate.py` output before and after

## Committing

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
- No `Co-Authored-By` trailers
- Sign your commits if possible (project uses SSH-key signing)

## What WORD-DRIFT is NOT

- Not a dictionary replacement -- depth over breadth; model the *change*, not the full current meaning
- Not an opinion graph -- every `drift:triggeredBy` link is a sourced, confidence-graded claim, not a fact
- Not bound to any one NLP system -- the `drift:` namespace stays tool-neutral
- Not a marketing resource -- "funky is cool" is a sense; "brand X uses funky" is out of scope

## Reporting issues

Open an issue at `https://github.com/XORwell/word-drift/issues` with:

- what you ran (commit hash)
- what you expected
- what you got
- `validate.py` output if relevant

For private or sensitive concerns: `research@nennemann.de`.

## Maintainer

Christian Nennemann -- `research@nennemann.de`. Single-maintainer for now;
co-maintainer onboarding is planned once the paper is submitted.
