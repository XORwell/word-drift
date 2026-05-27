# Federation smoke-test guide

This document explains how to run the queries under `queries/federated/` once
the word-drift QLever instance is running, and what results to expect.

## 1. Start the QLever endpoint

```bash
bash scripts/load-qlever.sh        # Docker, recommended
# or
bash scripts/load-qlever.sh --no-docker  # local qlever binaries
```

The server listens on `http://localhost:7019` by default.
Override the port with `QLEVER_PORT=<port>` before running the script.

Verify it is up:

```bash
curl -s 'http://localhost:7019/?cmd=stats' | python3 -m json.tool | head -20
```

---

## 2. Local queries (no network required)

These three queries work entirely within the loaded graph and should return
rows immediately.

### reframed-by-event.rq

Which trigger event reframed the most words?

```bash
curl -s -X POST http://localhost:7019 \
  -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/json' \
  --data-binary @queries/federated/reframed-by-event.rq \
  | python3 -m json.tool
```

Expected shape: rows with columns `trigger`, `triggerLabel`, `category`,
`eventYear`, `wordCount`, `words`. With only the two shipped examples,
COVID-related triggers appear twice (once each for the political and pandemic
categories) each reframing "Querdenker"; the funk trigger reframes "funk".
With the full showcase set loaded, political triggers should dominate.

### cross-lingual-same-direction.rq

Words in different languages that drifted in the same direction:

```bash
curl -s -X POST http://localhost:7019 \
  -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/json' \
  --data-binary @queries/federated/cross-lingual-same-direction.rq \
  | python3 -m json.tool
```

Expected shape: rows with `driftType`, `driftTypeLabel`, `word1`, `lang1`,
`year1`, `word2`, `lang2`, `year2`. With the two shipped examples, expect
one pejoration pair (Querdenker/de x any English pejoration if present) and
one amelioration pair (funk/en). Pairs grow quadratically as more examples
are added.

### trigger-category-breakdown.rq

Count of drift events per trigger category:

```bash
curl -s -X POST http://localhost:7019 \
  -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/json' \
  --data-binary @queries/federated/trigger-category-breakdown.rq \
  | python3 -m json.tool
```

Expected shape: rows with `category`, `categoryIRI`, `driftEventCount`.
With the two shipped examples, expect Political=1 (Querdenken-711), Pandemic=1
(COVID-19). Additional drift events can share a trigger, so the political
count will rise as the showcase set grows.

---

## 3. Federated query (requires network + Wikidata reachable)

### trigger-wikidata-enrich.rq

Enriches local trigger events with Wikidata labels, inception dates, and
countries via `SERVICE <https://query.wikidata.org/sparql>`.

QLever supports federated queries natively. Run it as any other query:

```bash
curl -s -X POST http://localhost:7019 \
  -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/json' \
  --data-binary @queries/federated/trigger-wikidata-enrich.rq \
  | python3 -m json.tool
```

Expected shape: rows with `trigger`, `triggerLabel`, `wdItem`, `wdLabel`,
`wdInception`, `wdCountry`, `localYear`.

With the two shipped examples, expect two rows:

| wdItem | wdLabel | wdInception | wdCountry | localYear |
|--------|---------|-------------|-----------|-----------|
| wd:Q115500066 | Querdenken 711 (movement) | 2020-04-XX | Germany | 2020 |
| wd:Q81068910 | COVID-19 pandemic | 2019-12-XX | (none or China) | 2020 |
| wd:Q164444 | funk (music genre) | ~1965 | United States | 1965 |

Cross-checking: if `wdInception` differs significantly from `localYear` (e.g.
more than 5 years), that flags a possible mistake in our `drift:eventDate` or
the wrong Wikidata item in `owl:sameAs`.

### Troubleshooting

- **QLever cannot reach query.wikidata.org**: check firewall / DNS from the
  Docker container. The SERVICE sub-query routes from the QLever container, not
  from the host.
- **Wikidata rate-limit (429)**: add a `User-Agent` header in the SERVICE
  request (not possible in plain SPARQL 1.1; contact your QLever build to
  configure a forwarded UA header).
- **SERVICE not supported on a plain rdflib run**: the federated query is
  intentionally excluded from `validate.py`'s glob (`queries/*.rq`). Only run
  it against a real SPARQL endpoint.
- **Timeout**: the Wikidata SPARQL endpoint enforces a 60-second timeout.
  If the graph has many trigger events, add a `VALUES ?wdItem { wd:Q... }` block
  to scope the sub-query to a subset.

---

## 4. Using the MCP qlever tool

If the `mcp-server-qlever` MCP server is configured to point at
`http://localhost:7019`, all four queries can be run interactively from
Claude Code:

```
claude mcp add qlever -- npx -y mcp-server-qlever -e http://localhost:7019
```

Then in a Claude Code session, paste the contents of any `.rq` file directly
into a `sparql_query` tool call.
