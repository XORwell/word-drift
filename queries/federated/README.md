# queries/federated/

This subfolder holds SPARQL queries that either:

1. use a `SERVICE` block to federate against the live Wikidata endpoint, or
2. perform cross-word / cross-language analyses that are conceptually separate
   from the per-word canonical queries under `queries/`.

## Why a subfolder, not queries/*.rq?

`validate.py` (and the CI green gate) globs **only** `queries/*.rq` (non-recursive):

```python
files = sorted(queries_dir.glob("*.rq"))
```

The `SERVICE`-based query (`trigger-wikidata-enrich.rq`) requires:
- a SPARQL 1.1 federation-capable endpoint (QLever or equivalent), and
- live network access to `https://query.wikidata.org/sparql`.

Running it offline inside rdflib raises `NotImplementedError` and would break
the CI gate that is supposed to be environment-independent. Placing it here
keeps the offline test suite green while making the query findable.

The three local queries in this folder (no SERVICE) could technically live in
`queries/`, but are grouped here because they are thematically part of the
"federation / cross-word analysis" feature set and are best documented and
run together. They have been verified to return rows against the current
ontology + examples graph.

## Files

| File | SERVICE? | Description |
|------|----------|-------------|
| `trigger-wikidata-enrich.rq` | YES | Pull Wikidata labels, inception dates, and countries for every `owl:sameAs`-linked trigger event. Cross-checks our `drift:eventDate`. |
| `reframed-by-event.rq` | no | Which trigger event reframed the most words? Joins drift events to triggers via `drift:CausalHypothesis` (aboutDrift/proposedTrigger), counts distinct words affected. |
| `cross-lingual-same-direction.rq` | no | Words in different languages that underwent the same `drift:driftType` (e.g. pejoration in both DE and EN). |
| `trigger-category-breakdown.rq` | no | Count drift events by trigger category (Political, Pandemic, Technology, Cultural, Media, Commercial). |

## Running these queries

See `scripts/federation-smoke.md` for step-by-step instructions, including
how to start the QLever endpoint and what result shapes to expect.

## Verifying the local queries offline

```bash
python3 -c "
import rdflib, glob
g = rdflib.Graph()
for f in sorted(glob.glob('ontology/*.ttl') + glob.glob('examples/*.ttl')):
    g.parse(f)
for q in ['reframed-by-event', 'cross-lingual-same-direction', 'trigger-category-breakdown']:
    rows = list(g.query(open(f'queries/federated/{q}.rq').read()))
    print(q, '->', len(rows), 'rows')
"
```
