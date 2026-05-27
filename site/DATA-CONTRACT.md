# WORD-DRIFT site data contract

The explorer (`explore.html`) consumes JSON emitted by `viz/export.py` and
copied into `site/` by `make graph`. There are three files. The split exists so
the explorer can paint immediately from a small core file and pull heavy
per-word detail lazily, instead of blocking first paint on the full 1.8 MB blob.

## Files

| File | Purpose | Loaded |
| --- | --- | --- |
| `graph.json` | Full union document (back-compat, unchanged shape). | Not needed by the split loader; kept for tools/back-compat. |
| `graph-core.json` | Everything for first paint, with LIGHT words (no heavy per-word detail). | On first paint. |
| `graph-detail.json` | Map `wordId -> heavy per-word fields`. | Lazily, or once in the background after first paint. |

## `graph-core.json`

Top-level keys (same shapes as in `graph.json`, minus heavy word detail):

- `meta` -- summary counts (identical to `graph.json.meta`)
- `driftTypes` -- SKOS drift-type concepts (identical)
- `facets` -- distinct filter values: `{language, driftType, connotation, evidenceType, source, quality}` (identical)
- `byDecadeType` -- stacked histogram `[{decade, type, n}]` (identical)
- `triggerImpact` -- per-trigger rollup `[{trigger, label, year, category, wordCount, words}]` (identical)
- `triggers` -- full trigger-event list, small (identical)
- `driftEventsFlat` -- flat drift-event records for the overview timeline + cross-lingual joins (identical)
- `words` -- LIGHT word objects, one per word:

```jsonc
{
  "id":              "https://w3id.org/word-drift/...",  // word IRI, key into graph-detail.json
  "writtenForm":     "Wolke",
  "language":        "de",          // or null
  "source":          "GfdS",        // primary source label
  "quality":         "high",        // "high" | "benchmark" | "detected"
  "sources":         ["GfdS"],      // union of all source labels
  "driftTypeLabels": ["Broadening"],// distinct drift-type labels for this word
  "yearStart":       1900,          // earliest year across senses/drifts/freq, or null
  "yearEnd":         2020,          // latest year across senses/drifts/freq, or null
  "hasTrigger":      true           // true if any drift event has a trigger
}
```

A LIGHT word does **not** carry `senses`, `driftEvents`, or
`frequencyObservations`. Fetch those from `graph-detail.json` by `id`.

## `graph-detail.json`

A single JSON object (map) keyed by word `id`. Every `id` in
`graph-core.json.words` has exactly one entry:

```jsonc
{
  "<wordId>": {
    "senses":                [ /* identical to the word's full senses */ ],
    "driftEvents":           [ /* identical to the word's full driftEvents */ ],
    "frequencyObservations": [ /* identical to the word's full freq obs */ ],
    "sources":               ["GfdS"]   // convenience copy of the union list
  }
}
```

### Per-word heavy field shapes (unchanged from `graph.json`)

- `senses[]`: `{id, glossEn, connotation, connotationId, firstAttested, attestedIntervalStart, attestedIntervalEnd}`
- `driftEvents[]`: `{id, wordId, senseFromId, senseToId, driftTypeLabel, driftTypeIds, year, yearEnd, confidence, triggerIds}`
- `frequencyObservations[]`: `{year, value}`

## Loader contract for the explorer

1. Fetch `graph-core.json`, render Overview + Triggers tabs, facets, and the
   word grid from the LIGHT `words` plus the shared aggregates.
2. When a word detail view is opened (or eagerly in the background after first
   paint), fetch `graph-detail.json` and look up `detail[word.id]` to get
   `senses` / `driftEvents` / `frequencyObservations`.
3. Field meanings are identical to the old `graph.json`; only their location
   moved. No keys were renamed.
