# WORD-DRIFT Visualization

Static, no-build-step visualization of the WORD-DRIFT knowledge graph.
Two views: a per-word sense timeline and a sense/trigger force-directed graph.

## Quick start

**Step 1 — export the graph data**

From the project root (requires `rdflib`; install with `pip install rdflib`):

```
python viz/export.py
```

This reads `ontology/*.ttl`, `examples/*.ttl`, and `data/*.ttl` (if present),
runs SPARQL-style extraction, and writes `viz/data/graph.json`.

**Step 2 — serve the viz directory**

```
python -m http.server 8000 -d viz
```

Then open: http://localhost:8000

The page uses `fetch()` to load `data/graph.json`, which requires a server
(`fetch()` does not work with `file://` URLs in most browsers).

## Files

| File | Purpose |
|------|---------|
| `export.py` | Loads RDF, builds `data/graph.json` |
| `index.html` | Single-page app shell, D3 v7 from CDN |
| `app.js` | D3 rendering: timeline + force graph |
| `style.css` | Dark-theme styling, legend, tooltip |
| `data/graph.json` | Generated export (not committed) |

## Views

**Timeline** (default view)

- Horizontal time axis from earliest sense to present
- Each sense is a coloured band starting at `firstAttested`
- Colour: green = positive, grey = neutral, red = negative connotation
- Drift events shown as curved arrows between senses, labelled by type
  (pejoration, amelioration, reversal, etc.)
- Trigger events shown as diamonds on a lower timeline strip with dashed
  vertical lines into the sense zone
- Frequency observations (when available) shown as a sparkline below the axis
- Hover any element for a tooltip with full details

**Force graph**

- Circles = senses (coloured by connotation)
- Diamonds = trigger events (orange)
- Solid edges = drift transitions (sense-to-sense), labelled by drift type
- Dashed edges = triggered-by links (sense to trigger event)
- Edge opacity reflects curator confidence (0.0-1.0)
- Drag nodes to explore; scroll to zoom; drag background to pan
- Hover any node for a tooltip

## Adding more words

Add Turtle files to `examples/` or `data/` following the pattern in
`examples/querdenker.ttl`, then re-run `python viz/export.py`.
