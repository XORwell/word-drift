# WORD-DRIFT explorer plugin API (`window.WD`)

This is the contract that view modules build against. The main script in
`explore.html` loads `graph-core.json`, sets up the Overview / Triggers /
Word Detail tabs, then publishes a global `window.WD` object and loads the view
modules (`compare.js`, `network.js`, `map.js`, `trends.js`, `exporter.js`) with
`<script defer>` AFTER itself, so `window.WD` always exists when a module runs.

A view module:

1. Lives in `site/assets/views/<name>.js`.
2. Wraps its code in an IIFE and guards `window.WD` (defensive, in case load
   order ever changes).
3. Calls `WD.registerView("<name>", { label, panelId, onActivate })` exactly
   once. That wires the existing tab button (`data-tab="<name>"`) and panel
   (`id="panel-<name>"`) to the view.
4. Renders into the `panelEl` it is handed in `onActivate`. It must NOT touch
   other panels, the topbar, or the facet sidebar (except via the documented
   `WD` helpers).

The four view tabs (`compare`, `network`, `map`, `trends`) and their empty
panels are already present in `explore.html`. `exporter.js` owns no panel; it
registers a toolbar button instead.

## Minimal view module

```js
(function () {
  "use strict";
  if (!window.WD || typeof WD.registerView !== "function") return;
  WD.registerView("compare", {
    label: "Compare",          // optional; relabels the tab button
    panelId: "panel-compare",  // must match the panel element id
    onActivate(panelEl) {
      // Called each time the tab is shown. First call = build; later calls
      // may be used to refresh to current data/filters/width.
      panelEl.innerHTML = "";
      const w = WD.words.find(x => x.writtenForm === "Kaiser");
      WD.getDetail(w).then(full => {
        panelEl.textContent = full.senses.length + " senses";
      });
    },
  });
})();
```

## Data shapes

Field meanings are defined in `site/DATA-CONTRACT.md`. Summary of what you get:

### A LIGHT word (`WD.words[i]`, from `graph-core.json`)

```jsonc
{
  "id":              "https://w3id.org/word-drift/resource/word-kaiser", // IRI, key into detail
  "writtenForm":     "Kaiser",
  "language":        "de",            // or null
  "source":          "Curated",       // primary source label
  "quality":         "high",          // "high" | "benchmark" | "detected"
  "sources":         ["Curated"],     // union of all source labels
  "driftTypeLabels": ["metonymization"], // distinct drift-type labels
  "yearStart":       27,              // earliest year, or null (negative = BC)
  "yearEnd":         1881,            // latest year, or null
  "hasTrigger":      true
}
```

A light word does NOT carry `senses`, `driftEvents`, or
`frequencyObservations`. Fetch those with `WD.getDetail(word)` (see below).

### A heavy/merged word (after `WD.getDetail(...)`)

The same object, now also carrying:

- `senses[]`: `{ id, glossEn, connotation, connotationId, firstAttested, attestedIntervalStart, attestedIntervalEnd }`
- `driftEvents[]`: `{ id, wordId, senseFromId, senseToId, driftTypeLabel, driftTypeIds, year, yearEnd, confidence, triggerIds }`
- `frequencyObservations[]`: `{ year, value }`
- `__detailMerged: true` (internal marker; treat as read-only)

### A trigger (`WD.triggers[i]`)

```jsonc
{
  "id":              "https://w3id.org/word-drift/resource/trigger-kaiser-augustus",
  "label":           "Establishment of the Roman imperial title under Augustus",
  "date":            27,             // year, or null (negative = BC)
  "category":        "political",
  "wikidataSameAs":  "http://www.wikidata.org/entity/Q1405", // or null
  "description":     "From 27 BC onward ..."
}
```

### A `driftEventsFlat` entry (`WD.driftEventsFlat[i]`)

One record per (word, drift event). This is the join layer used for the
overview beeswarm, cause colouring, and cross-lingual links. Available from
`graph-core.json` for every word (no detail fetch needed).

```jsonc
{
  "word":       "Kaiser",
  "lang":       "de",
  "type":       "metonymization",     // drift-type label (first if multi)
  "year":       27,
  "fromConn":   "neutral",            // connotation before (or null)
  "toConn":     "neutral",            // connotation after (or null)
  "hasTrigger": true,
  "source":     "Curated",
  "quality":    "high",
  "causes": [                         // sorted by confidence, strongest first
    {
      "triggerLabel": "Establishment of the Roman imperial title under Augustus",
      "triggerYear":  27,
      "category":     "political",
      "evidence":     ["lexicographic note"], // free strings; map via WD.evidenceRung
      "confidence":   0.85                     // 0..1, or absent
    }
  ]
}
```

### A `triggerImpact` entry (`WD.triggerImpact[i]`)

```jsonc
{
  "trigger":   "https://w3id.org/word-drift/resource/trigger-www-mosaic", // trigger IRI
  "label":     "World Wide Web and Mosaic browser launch",
  "year":      1993,
  "category":  "technological",
  "wordCount": 4,
  "words":     ["Netz", "surf", "surfen", "web"]   // written forms
}
```

`byDecadeType` is `[{ decade, type, n }]`; `facets` is
`{ language, driftType, connotation, evidenceType, source, quality }` (arrays of
distinct values); `meta` carries the summary counts.

## `window.WD` members

### Data (read-only)

| Member | Type | Notes |
| --- | --- | --- |
| `WD.core` | object | The whole `graph-core.json` document. |
| `WD.words` | `LightWord[]` | Getter. All light words. |
| `WD.triggers` | `Trigger[]` | Getter. |
| `WD.driftEventsFlat` | `FlatEvent[]` | Getter. |
| `WD.triggerImpact` | `TriggerImpact[]` | Getter. |
| `WD.meta` | object \| null | Getter. Summary counts. |
| `WD.facets` | object \| null | Getter. Distinct facet values. |
| `WD.byDecadeType` | `[{decade,type,n}]` | Getter. |

### Lazy detail

| Member | Signature | Notes |
| --- | --- | --- |
| `WD.getDetail(wordOrId)` | `(string\|LightWord) -> Promise<HeavyWord\|null>` | Fetches `graph-detail.json` once (cached), merges `senses` / `driftEvents` / `frequencyObservations` onto the word, resolves to it. Already-merged words resolve immediately. |

```js
WD.getDetail("https://w3id.org/word-drift/resource/word-kaiser")
  .then(w => console.log(w.senses, w.driftEvents, w.frequencyObservations));
```

### Lookups (synchronous, light data)

| Member | Signature | Notes |
| --- | --- | --- |
| `WD.wordById(id)` | `(string) -> LightWord\|null` | |
| `WD.triggerById(id)` | `(string) -> Trigger\|null` | |
| `WD.flatForWord(word)` | `(LightWord) -> FlatEvent[]` | Pre-indexed; do not scan `driftEventsFlat` yourself. |

### Navigation

| Member | Signature | Notes |
| --- | --- | --- |
| `WD.openWord(wordOrId)` | `(string\|LightWord) -> void` | Opens the Word Detail tab (lazy-loads detail, shows an inline loader if needed). Updates URL `?word=` + persists last word. |
| `WD.showTrigger(triggerId)` | `(string) -> boolean` | Switches to Triggers tab and renders that trigger's detail. Returns false if unknown. |
| `WD.switchTab(name)` | `(string) -> void` | `"overview"\|"triggers"\|"detail"\|"compare"\|"network"\|"map"\|"trends"`. |

### View registration

| Member | Signature | Notes |
| --- | --- | --- |
| `WD.registerView(name, def)` | `(string, {label?, panelId?, onActivate}) -> boolean` | `onActivate(panelEl)` is required and fires on every activation (first build + subsequent shows + resize). Returns false if `onActivate` is missing. |
| `WD.registerToolbarButton(opts)` | `({label, title?, onClick}) -> HTMLButtonElement\|null` | For utility modules (e.g. `exporter.js`). Appends a button to the topbar actions. |

### Shared helpers (render consistently with the core)

| Member | Signature | Notes |
| --- | --- | --- |
| `WD.escHtml(str)` | `(any) -> string` | HTML-escape. ALWAYS use before injecting data into `innerHTML`. |
| `WD.makeActivatable(el, fn)` | `(HTMLElement, () => void) -> void` | Adds `role=button`, `tabindex=0`, click + Enter/Space handlers. |
| `WD.dtColor(typeStr)` | `(string) -> string` | Drift-type hex colour (handles multi-type and null). |
| `WD.connColor(label)` | `(string) -> string` | Connotation hex colour (positive/neutral/negative). |
| `WD.causeColor(flatEventNode)` | `(FlatEvent) -> string` | Top-cause colour for a flat event (matches the overview cause lens). |
| `WD.fmtYear(y)` | `(number\|null) -> string` | Renders negative years as `"350 BC"`, null as `"?"`. |
| `WD.evidenceRung(rawStr)` | `(string) -> number` | Maps an evidence string to a ladder index 0..4, or -1. |
| `WD.EVIDENCE_LADDER` | `[{key,label}]` | Weakest to strongest: Speculative, FrequencyCorrelation, ChangeSignalAlignment, LexicographicNote, ScholarlyAttestation. |
| `WD.prefersReducedMotion` | `boolean` | True if the user requested reduced motion. Disable simulations/animations when set. |
| `WD.colors` | object | `{ DT_COLORS, CONN_COLORS, TRIGGER_COLOR, DRIFT_EDGE_COLOR, BG_COLOR, CAUSE_PALETTE, CAUSE_COLOR_MAP }`. |

## Conventions for module authors

- D3 v7 is already loaded globally (`window.d3`). Do not bundle another copy or
  add new libraries.
- No em-dashes in any user-facing text.
- Honour `WD.prefersReducedMotion`: skip force-simulation animation (run it to
  convergence synchronously, then paint once) and avoid decorative transitions.
- Size charts to `panelEl.clientWidth` and re-render on `onActivate` (it fires
  on resize too).
- Escape every dynamic string with `WD.escHtml` before `innerHTML`.
- Reuse `WD.dtColor` / `WD.connColor` / `WD.causeColor` so colours stay
  consistent with the Overview and legend.
- Treat `WD.core` and all data arrays as read-only. Never mutate a word except
  via `WD.getDetail` (which merges detail in place, intentionally).
