# 03 — Visualisations

> A visualisation in word-drift is an instrument, not a dashboard. Each one answers a specific historical-linguistic question and refuses to answer the questions next to it. If a chart could carry the logo of a SaaS company without anyone noticing, it is the wrong chart.

Scope: the ten target visualisations from the MASTER PROMPT, ordered from "extension of what 2.x already does" to "entirely new ground". Each is specified well enough to be implemented in isolation by an agent without re-reading the rest of the plan tree. Cross-references point at `01-ontology-delta.md` (data shapes), `02-metrics.md` (derived quantities), and `05-milestones.md` (when it ships).

Design language (binding, from `00-vision.md §5`): linguistic atlases, scientific observatories, museum archives, historical cartography, systems diagrams, editorial infographics, dark academia, semantic archaeology. Visual reference points: the *Sprachatlas des Deutschen Reichs*, Minard's flow maps, Tufte's small multiples, the NYT graphics desk's archival reconstructions, *Times Literary Supplement* timelines. Out of scope: startup dashboards, crypto aesthetics, generic AI gradients, gamification, emoji-as-UI.

---

## 1. Semantic Drift Timeline (with historical overlay)

**Tagline.** A single word's sense trajectory across centuries, anchored to the historical events that may have shaped it.

**What it shows.** For one word: which senses were attested when, with which connotation, and which dated historical events plausibly triggered each shift. Answers *"What did this word do, and when, and against what backdrop?"*.

**Data needed.**
- `senses[]` with `firstAttested`, `attestedIntervalStart/End`, `connotation` (from 2.x `graph-detail.json`).
- `driftEvents[]` with `year`, `driftTypeLabel`, `triggerIds` (2.x).
- `frequencyObservations[]` (2.x).
- New in 3.0: `drift:occurredInGroup` on drift events (`01-ontology-delta.md → group module`), so the timeline can split into per-group strands when group attributions exist.
- Trigger events from `triggers` (2.x, already in `graph-core.json`).

**Visual idiom.** Horizontal time axis (log-warped before 1800, linear after — historical-linguistic convention). Senses rendered as horizontal *attestation bands*, not lines; the band's vertical opacity encodes confidence. Drift events are arrowheads landing on the band where the new sense begins. Historical triggers appear as a separate ruled strip below the senses ("the chronicle band"), with thin connector lines reaching up to the drift arrows they are hypothesised to explain. This idiom fits because lexical attestation is fundamentally an *interval* phenomenon, not a point — a sense was current "from roughly X to roughly Y", and a line falsely implies single-year precision the sources do not have.

**Interactions.**
- Hover a band: gloss, source, evidence ladder rung.
- Hover a trigger: chronicle entry, list of affected words.
- Click a trigger: filter the chronicle band to that event's category (war, technology, legal, …) across the whole period.
- Brush a date range: zoom; the chronicle band re-densifies inside the brush.
- Toggle "Show cause links" (carried over from 2.x): explicit connector lines from drift arrows to triggers.

**Status.** Extends the existing 2.x word-detail timeline. Lives alongside it through M3; gains the per-group split in **M4**.

**Aesthetic notes.** Palette is ink-on-parchment for the chronicle band (warm neutral background, near-black lines) and a three-step sequential cool ramp for connotation (positive → neutral → negative is *not* green → grey → red; use blue-grey → grey → ochre-grey to avoid moral coding). Sense bands use a darker stroke and a 30%-opacity fill, the chronicle band uses italic serif labels. No gradients beyond the connotation ramp.

**Must NOT.**
- Must not draw a single line through the senses, which would impose one trajectory.
- Must not colour positive green or negative red.
- Must not present the chronicle band as causal proof; the connector lines are *hypotheses*, labelled with their evidence-ladder rung from 2.x.

---

## 2. Meaning Distribution Graph

**Tagline.** Sense proportions for one word over time, with majority and minority strands made explicit.

**What it shows.** How the shares of competing senses moved against each other. Answers *"When did sense B overtake sense A, and how steep was the cross-over?"*.

**Data needed.**
- `drift:MeaningAttribution` records keyed by `(sense, time-bucket, group?)` with `drift:weight` and a confidence interval — see `01-ontology-delta.md → group module / distribution module`.
- Aggregated to `/graph-distribution.json` per word (new endpoint per M4).
- Falls back to a single series when no group attributions exist.

**Visual idiom.** Stacked area chart on a normalised (0–1) y-axis, with the *minority floor* drawn as a hatched zone — anything below 5% is rendered with a diagonal-line pattern rather than a solid fill, so marginalised senses are visible without being inflated. Confidence intervals appear as a lighter band above and below each stratum's top edge. Optional small-multiples mode renders one stacked area per group side by side at identical scale.

Why this idiom: stacked area is the canonical chart for compositional change, and the hatched minority floor solves the standard stacked-area failure (small strata become invisible). Small multiples handle the multi-group case better than a stacked-area-of-stacked-areas, which is unreadable.

**Interactions.**
- Hover a stratum: gloss, share at that year, CI, top three source citations.
- Click a stratum: pins it; other strata fade to 30% so the pinned one's trajectory reads cleanly.
- Toggle small-multiples vs single stack.
- Brush a time range: applies as a global filter to coordinated views (see *Cross-viz coordination* below).

**Status.** **M4.** Load-bearing artefact of that milestone.

**Aesthetic notes.** Categorical palette (one hue per sense), at most six hues; if a word has more than six senses, the remainder collapses into a labelled "other senses" stratum. Hue assignment is stable per sense IRI across views. Confidence-interval bands are 40% opacity of the stratum hue, never grey. Hatching for the <5% floor is at 45° at 1px stroke; ColorBrewer "Set2"-like palette for moderate vibrance without saturation.

**Must NOT.**
- Must not pick a "winning" sense via a bold label or arrow. The viewer reads winners off the chart; the chart does not editorialise.
- Must not hide the minority floor by clipping it.
- Must not animate the stack rebuilding on load (a one-time draw, not a reveal sequence; this is a research instrument, not a reel).

---

## 3. Semantic Fragmentation Index

**Tagline.** A single number, per word, per moment: how fractured is the meaning right now.

**What it shows.** The trajectory of the fragmentation index (see `02-metrics.md → semantic_fragmentation_index`) over time, plus a glanceable current-state indicator. Answers *"Is this word coherent today, or is it pulling itself apart?"*.

**Data needed.**
- Precomputed `semantic_fragmentation_index` per word per time-bucket.
- The metric itself depends on `drift:MeaningAttribution` weights aggregated per group (`02-metrics.md`).
- Exposed via the metric REST endpoint scheduled for **M3**.

**Visual idiom.** A sparkline (50–80px tall) showing the index from earliest attestation to today, with a single bold tick marking the present value, and a discrete categorical badge ("coherent" / "drifting" / "fragmenting" / "fractured") derived from index thresholds defined in `02-metrics.md`. The sparkline sits at the top of the word-detail view as a status strip, not a chart panel. The badge uses neutral typographic labels, not coloured pills.

Why this idiom: fragmentation is a *summary statistic*. A sparkline plus a categorical badge is the established Tufte idiom for "one number with context". Anything larger over-claims.

**Interactions.**
- Hover the sparkline: year-by-year index value and which group contributed most to that period's fragmentation.
- Click the badge: opens a glossary entry explaining the thresholds and the formula, citing `02-metrics.md`.

**Status.** **M3** (initial plot on word detail), refined in **M4** when group splits land.

**Aesthetic notes.** Monochrome. The sparkline uses the body-text colour, the current-value tick uses a single accent hue (the site's existing `--accent`). The badge is set in small-caps in the body font, no background fill.

**Must NOT.**
- Must not use a gauge, dial, or speedometer.
- Must not assign positive/negative valence to fragmentation. A word can be fractured for excellent reasons; the index is descriptive.

---

## 4. Semantic Constellation Map

**Tagline.** The neighbourhood of a word: which senses sit near which, and which words occupy adjacent semantic space.

**What it shows.** The topology of a word's senses and its semantic neighbours, projected into 2D. Sense clusters appear as constellations; overlaps appear as shared edges or bridge nodes. Answers *"What semantic territory does this word actually occupy, and who are its neighbours?"*.

**Data needed.**
- Sense embeddings (per `drift:Sense`) — either from the existing computational change signals or from a declared embedding model logged with version (`01-ontology-delta.md → provenance`, `ADR-0004`).
- `drift:relatedSense` and `drift:senseSibling` cross-references (2.x already has cross-lingual siblings).
- Group attributions to colour-tint clusters.

**Visual idiom.** Force-directed graph with sense nodes as filled discs, words as outlined discs, and edges weighted by embedding similarity (above a threshold to avoid hairball). Clusters are *visually grouped* by a translucent convex hull behind related senses — this is the constellation. Edge thickness is similarity; node size is attestation frequency. The layout is computed once and stored, not recomputed on every load, so the same word always looks the same (reproducibility over animation).

Why this idiom: force-directed is the standard for semantic neighbourhoods, and the convex-hull overlay is what turns a generic graph into something that reads like an *atlas plate*. The "constellation" metaphor is literal: groupings of bright points under a faint membership halo.

**Interactions.**
- Hover a node: gloss, attestation interval, group attributions.
- Click a node: re-centres the layout on that node (recomputed once and cached).
- Lasso a region: pins those senses as a focus group; coordinated views filter to them.
- Toggle "show bridges": highlights senses that sit on two cluster hulls simultaneously.

**Status.** Unscheduled (post-M8 candidate; depends on agreed embedding-model provenance contract).

**Aesthetic notes.** Dark academia palette: deep navy or near-black background, ivory nodes, hull fills at 15% opacity in a muted six-colour categorical scheme. Labels in a serif typeface, small caps for word labels, italic lowercase for sense glosses. No glow effects.

**Must NOT.**
- Must not animate on idle ("breathing" graphs are dashboard kitsch).
- Must not use a starfield background image.
- Must not produce a new layout on every reload — the same word renders identically each time.

---

## 5. Semantic Civil War View

**Tagline.** When a word splits into incompatible readings, this view holds both readings on the page at the same time, without picking a side.

**What it shows.** Two (or more) group-conditioned readings of the same word, the corpus evidence each side cites, and the timeline of when the bifurcation hardened. Answers *"Where exactly is the disagreement, and what does each side think the word means?"*.

**Data needed.**
- `drift:MeaningAttribution` records grouped by `drift:Community` (from `01-ontology-delta.md → group module`).
- `group_divergence` metric (`02-metrics.md`).
- Top-N exemplar corpus spans per group, with provenance.
- A bifurcation date estimated by the divergence-velocity metric.

**Visual idiom.** Mirrored-axis layout (a "Sankey-like split" or "ridge plot mirrored across a centre line"). The y-axis is time, descending. Down the centre runs the word itself as a vertical spine. To the left and right, each group's dominant sense at each moment is rendered as a horizontal bar whose width is that sense's share within that group. The space between the spine and each side carries quoted exemplar spans (one or two short attestations per decade) in small caps. When a bifurcation event is detected, a horizontal *fault line* is drawn across both sides at that y-coordinate, labelled with the date and the divergence value.

Why this idiom: a mirrored axis is the only honest way to show "two readings of the same thing". The fault-line metaphor is borrowed from geological stratigraphy (semantic archaeology aesthetic) and is the correct register for a hardening disagreement.

**Interactions.**
- Hover a bar: full gloss + CI for that group at that time.
- Click an exemplar span: opens its source citation.
- Toggle "show neutral middle": when present, attributions that resist group assignment appear in a narrow centre column.
- Filter to two specific groups: the view degrades cleanly when more than two groups have annotations.

**Status.** Unscheduled (depends on M4 + a richer group taxonomy than M2 will land).

**Aesthetic notes.** Diverging palette where the *axis is sense-similarity-to-historical-baseline*, not moral valence. Each side uses a distinct hue (cool slate and warm ochre, neither traditionally "good" nor "bad"). The fault line is set in a single accent colour shared with the fragmentation badge.

**Must NOT.**
- Must not label sides with moral terms ("extremist", "mainstream", "rational", …). Sides carry the literal group label from the KG (e.g. "skeptik-community-de", "mainstream-press-de") and nothing else.
- Must not use red and blue (loaded with political coding in every relevant audience).
- Must not animate the bifurcation as a dramatic split. The fault line is drawn statically.

---

## 6. Geographic Semantic Maps

**Tagline.** The same word, in different countries or regions, can mean substantially different things.

**What it shows.** Region-conditioned dominant sense of a word, with a secondary layer for divergence intensity. Answers *"Where does this word mean what?"*.

**Data needed.**
- `drift:Region` (from `01-ontology-delta.md → geography module`; **M5**).
- Region-conditioned `drift:MeaningAttribution` weights.
- Country boundaries (Natural Earth low-res, public domain).
- For M5 the granularity is country-level; sub-national is explicitly deferred.

**Visual idiom.** A *categorical choropleth* coloured by the dominant sense in each region, plus an overlaid *proportional-symbol layer* sized by the within-region semantic entropy (how contested the meaning is locally). A region where one sense dominates 95% gets a flat fill and no symbol; a region where three senses share the field gets the same flat fill (its plurality sense) but a prominent overlaid symbol signalling internal disagreement. This is the *Sprachatlas* idiom adapted: a single colour per region (the convention of historical dialect atlases) with a modern entropy overlay.

Why this idiom: choropleth alone hides intra-region disagreement; proportional-symbol alone hides what people there actually mean. Both layers together honour both questions.

**Interactions.**
- Hover a region: full distribution + CI for that region.
- Click a region: drills into the meaning-distribution graph filtered to that region.
- Toggle projection: equal-area (Eckert IV) default; Mercator only when explicitly requested (this is a research map, not a navigation map).
- Date slider: snapshots of regional meaning per decade.

**Status.** **M5.**

**Aesthetic notes.** Categorical palette identical to the meaning-distribution graph's sense palette, so a sense is the same colour everywhere it appears. Symbol overlay is monochrome (the site's accent), sized by entropy with a discrete five-step scale, not continuous. Use Eckert IV by default. Use a colour-blind-safe categorical scheme (ColorBrewer "Dark2" or "Set2").

**Must NOT.**
- Must not use Mercator by default. Mercator distorts the geography of meaning by inflating the global north.
- Must not display country borders the same weight as data layers (borders are 0.5px, data fills are dominant).
- Must not extrapolate to regions with no attributions. Missing data renders as a neutral cross-hatch, not as "neutral" or "absent meaning".

---

## 7. Platform Semantic Divergence

**Tagline.** A word on Reddit is not the same word in *Die Zeit*. This view holds the difference up to a microscope.

**What it shows.** How a word's sense distribution differs across platforms (Reddit, TikTok comments, newspaper corpora, academic prose, parliamentary speech). Answers *"Which platform invented the new sense, and how fast did it leak into others?"*.

**Data needed.**
- `drift:Platform`, `drift:CorpusContext`, `drift:Register` (from `01-ontology-delta.md → platform module`; **M6**).
- Platform-conditioned `drift:MeaningAttribution`.
- Cross-platform semantic distance metric (`02-metrics.md`).

**Visual idiom.** A *bumps chart* (also called a slope graph): one column per platform along the x-axis, one row per sense, and a thin band per sense whose height in each column is that sense's share on that platform. Bands cross when a sense's prominence flips between platforms. A time slider scrubs across years, redrawing the bumps. Above the bumps, a small *velocity arrow strip* shows which direction sense-shares are moving between adjacent platforms at the current year (e.g. "Reddit → mainstream press, lagging by 14 months").

Why this idiom: bumps charts are the canonical way to show rank-and-share comparison across discrete categories with shared semantics — they are the *Tour de France stage chart* for words. The velocity strip turns a static comparison into the dynamic story ("Reddit gets there first, broadsheets follow").

**Interactions.**
- Hover a band: platform-specific gloss + top exemplar from that platform's corpus.
- Click a platform column header: filters all coordinated views to that platform.
- Time slider: continuous; the bumps redraw as the year changes.
- Toggle "show lag arrows": the velocity strip is opt-in to avoid clutter.

**Status.** **M6.**

**Aesthetic notes.** Same sense-hue palette as views #2 and #6 (sense identity is preserved across views). Platform columns are typographic, not iconographic (no logos, no platform colours — those would import platform branding into a research instrument). Use Reddit/TikTok/etc. as plain set-in-italic labels.

**Must NOT.**
- Must not use platform brand colours.
- Must not display platform icons or logos.
- Must not editorialise platforms as "high-quality" or "low-quality" sources. The viz shows what each platform's corpus *contains*, not what it is worth.

---

## 8. Emotional Semantic Heatmap

**Tagline.** Emotional loading of a word over time, decomposed into named affective dimensions.

**What it shows.** A heatmap of a word's emotional framings (fear, irony, hostility, admiration, neutrality, …) across time, optionally split by group. Answers *"When did this word turn ironic? When did it turn hostile? Did its denotation move, or just its affect?"*.

**Data needed.**
- `drift:EmotionalFraming` with `drift:framingType`, `drift:valence`, `drift:loading` (from `01-ontology-delta.md → emotion module`; **M7**).
- Each framing carries evidence (corpus span or model output with declared model + version + prompt — see `ADR-0004`).

**Visual idiom.** A *small-multiples heatmap grid*: one row per framing dimension, x-axis is time, cell colour encodes loading intensity (sequential single-hue ramp per dimension), cell saturation encodes evidence strength. Adjacent to the heatmap, a parallel sparkline of denotation movement (sense-distribution change rate) is drawn at the same time scale, so the eye can compare "did meaning move?" against "did affect move?".

Why this idiom: heatmaps are right for "intensity over time on many categorical axes". The denotation sparkline alongside is the load-bearing comparison — without it, the heatmap risks implying emotion *is* meaning.

**Interactions.**
- Hover a cell: framing type, year-bucket, loading value, top exemplar span with model + version stamp.
- Click a row: pins that framing dimension; other rows fade.
- Toggle "split by group": each row splits into per-group sub-rows.
- Filter by evidence rung (only show framings backed by corpus, hide model-only).

**Status.** **M7.**

**Aesthetic notes.** Each framing dimension gets its own *sequential* hue ramp (ColorBrewer "YlOrBr" for hostility, "PuBu" for admiration, neutral grey for neutrality, etc.). Sequential, not diverging — emotional loading is an intensity, not a polarity to be split. Saturation encodes evidence strength so that low-evidence cells look correctly faded.

**Must NOT.**
- Must not collapse all emotions into a single "sentiment" score. Sentiment is a denuded dimension; the whole point of this view is to recover the lost dimensions.
- Must not assert framings without showing the rung of the evidence ladder for each cell.
- Must not present model-derived framings indistinguishably from corpus-attested ones.

---

## 9. Memetic Mutation Timeline

**Tagline.** How a word travelled through internet culture: ironic appropriation, copypasta crystallisation, in-group signal collapse.

**What it shows.** The discrete memetic mutation events that transformed a word's meaning on online platforms, with the mutation mechanism named explicitly. Answers *"How did this word become a meme, and what mechanism did the work?"*.

**Data needed.**
- `drift:MemeticMutation` subtypes of `drift:DriftEvent` (from `01-ontology-delta.md → memetic module`; **M8**).
- Subtypes: `drift:IronicAppropriation`, `drift:CopypastaCrystallisation`, `drift:InGroupSignalCollapse`, `drift:AlgorithmicAmplification`.
- Per-event provenance: thread, platform, date, exemplar.

**Visual idiom.** A vertical *event ribbon* (timeline reads top-to-bottom, the convention for editorial long-reads). Each mutation event is a horizontal card pinned to its date; the card carries the mutation mechanism as a set-in-italic label, a one-sentence editorial gloss, the exemplar quote, and a thin arrow pointing to the next event. The ribbon's right margin carries a continuous fragmentation-index sparkline running at the same date scale, so the reader can see whether each mutation made the word more or less coherent overall.

Why this idiom: memetic mutation is fundamentally *narrative* — it is best told as an editorial timeline, the form newspapers use for "how a story broke". Cards-with-arrows is honest about discreteness; a continuous chart would falsely smooth a stepwise phenomenon.

**Interactions.**
- Hover a card: full provenance (thread URL if licensed for display, otherwise just date + platform + screenshot description).
- Click the mechanism label: filters the ribbon to that mechanism class across the entire corpus.
- Date jump: anchor links per decade.

**Status.** **M8.**

**Aesthetic notes.** Editorial typography: serif body, small-caps mechanism labels, generous line height. Card background is the parchment-neutral of view #1's chronicle band. Mechanism labels are typographically distinguished, not colour-distinguished, because there is no natural ordering of mutation mechanisms. Exemplars are set in a monospaced face to mark them as quoted material.

**Must NOT.**
- Must not use animated GIFs of the actual memes (legal, ethical, and aesthetic reasons).
- Must not editorialise memes as "good" or "bad" content. Mechanism is descriptive.
- Must not omit the mutation mechanism — a memetic timeline without named mechanisms is just a list of dates.

---

## 10. Semantic Cemetery

**Tagline.** Words whose historically dominant meaning is now a minority reading: an archival register, not an elegy.

**What it shows.** A curated, filterable list of words whose dominant-historical sense now accounts for less than 5% of attributions, presented with the dignity of an archive entry. Answers *"Which meanings are receding, and what is replacing them?"*.

**Data needed.**
- `drift:SemanticCemetery` SPARQL *view* (not a class) returning words satisfying `historicalDominant.currentShare < 0.05`. See `02-metrics.md`.
- For each entry: the old sense (gloss, interval of dominance, last attestation), the current dominant sense, the mutation event(s) that mediated the transition.

**Visual idiom.** A *register* — typographically modelled on a museum inventory or a finding-aid index. Each entry is a card laid out in three columns: left column carries the word as a heading and the old sense gloss in italic; centre column carries the dominance interval ("dominant 1870–1968") and the last firmly-attested year; right column carries the current dominant sense with its present share. A small horizontal "decline curve" across the bottom of each card shows the old sense's share over time as a single sparkline. The whole page reads as an archival index, not as a graveyard.

Why this idiom: an archival register honours the descriptive purpose without inviting elegy. The decline sparkline is data; the layout is *paper-like*; the typography is the editorial signal.

**Interactions.**
- Filter by language, by century-of-decline, by mutation mechanism.
- Click an entry: opens the full word-detail view with the timeline (view #1) pre-scrolled to the dominance interval.
- Sort by current share, by length of dominance, or by recency of decline.

**Status.** **M8.**

**Aesthetic notes.** Strictly typographic. Single near-black ink colour on parchment background. No category colours. The sparkline is the same near-black, no fill. The page reads as a printed index, not as a web app.

**Must NOT.**
- Must not use funeral metaphors (tombstones, crosses, RIP, dates-in-parentheses styling).
- Must not romanticise meaning-loss as cultural decline. The register includes words whose receding meaning was harmful (slurs, propaganda terms); their decline is not a loss.
- Must not exclude words on the basis that their old meaning is unfashionable to mention.

---

## Cross-viz coordination

Coordinated views share state via a single in-page *selection bus* (a small pub-sub on the page, not a framework store). Three coordinated selections are supported in M4 and grow per milestone:

- **Word selection.** Opening a word from any view scrolls the word-detail panel into focus and propagates the word id to every view that supports word context.
- **Time-range brush.** Brushing in view #1, #2, or #3 emits a `time:[from,to]` selection that views #6, #7, and #9 honour as a soft filter.
- **Group selection.** Pinning a group in view #2 or #5 emits a `group:<id>` selection that views #6, #7, #8 honour as a soft filter; geographic view #6 honours it as a hard filter (regions where the group has no attributions render as missing-data hatch).

Selection is *transparent*: an "active filters" strip across the top of the explorer lists every active selection with an x-to-remove, mirroring the existing 2.x `#active-filters-bar`. No view consumes a filter silently.

ASCII sketch of the selection bus:

```
[view #2 brush 1980-2010]
        |
        v
+---------------------+
|  selection bus      |
|  word: Querdenker   |
|  time: 1980-2010    |
|  group: -           |
+---------------------+
    |    |    |
    v    v    v
 #1 ok  #6 ok  #7 ok  (#4 ignores time, #5 ignores time, #10 ignores time)
```

---

## Frontend tech notes

The current site is plain HTML + JS with D3 v7 loaded as a vendored asset and a small `WD.registerView()` plugin registry (`site/assets/views/API.md`). 3.0 stays inside this surface; introducing a framework is rejected by default.

**Default for 3.0:** D3 v7 plus, where the chart type fits, **Observable Plot** loaded the same way (vendored, no build step). Plot is a 25KB grammar-of-graphics layer over D3 that gives small-multiples, faceting, and ordinal scales declaratively in a few lines, and degrades cleanly into raw D3 when something custom is needed (constellation hulls, mirrored-axis civil-war view).

**Per-viz tech choice:**

| Viz | Tech |
|-----|------|
| 1. Semantic drift timeline | D3 (extend existing 2.x renderer). |
| 2. Meaning distribution graph | Observable Plot `area()` + `faceted`. |
| 3. Fragmentation index | Inline SVG sparkline, no library. |
| 4. Constellation map | D3 force layout + Canvas for nodes when count > 500; SVG otherwise. |
| 5. Civil-war view | D3 (mirrored axis is not in Plot's vocabulary). |
| 6. Geographic map | D3 + Natural Earth TopoJSON; Plot for the legend small-multiples. |
| 7. Platform divergence | Observable Plot bumps via `lineY({channels})`. |
| 8. Emotional heatmap | Observable Plot `cell()` faceted by framing dimension. |
| 9. Memetic timeline | Plain HTML + CSS grid; no D3 (this is editorial layout, not data viz). |
| 10. Semantic cemetery | Plain HTML + CSS grid + a tiny inline SVG sparkline per entry. |

Canvas is reserved for the constellation map's node count crossing ~500 — every other view stays SVG for accessibility and screenshot fidelity.

**No build step.** Vendor Plot's UMD bundle into `site/assets/vendor/` alongside D3. The plugin registry keeps each view a small, independent file.

**Door left open.** If a future view legitimately needs reactivity across many small components (the cross-viz coordination grows beyond ~5 views), we re-evaluate with an ADR — likely Lit, never React. We do not introduce SvelteKit, Next.js, or any router.

---

## Accessibility

Every viz must pass the following before its milestone is marked done:

- **Colour-blindness.** Categorical palettes are ColorBrewer-derived and verified against deuteranopia and protanopia simulators. Diverging palettes (views #5, #8) use blue/ochre or blue/orange, never red/green. Sequential palettes (views #3, #7, #8) are single-hue.
- **Screen-reader story.** Each viz exposes an associated `<figure>` with a `<figcaption>` containing a two-sentence prose summary auto-generated from the data ("Three senses share this word, the dominant being X with 62%, with sense Y rising from 5% to 31% between 2010 and 2024."). The full chart is wrapped in a `role="img"` with an `aria-labelledby` pointing at the caption, and a *data table fallback* is reachable via a "Show table" toggle in the chart header.
- **Keyboard navigation.** Every interactive element (hover targets, brush handles, toggles) has a keyboard equivalent: arrow keys move between data points, Enter activates, Esc clears selection. Focus rings are visible (the existing site's 2px solid focus style).
- **Reduced motion.** `prefers-reduced-motion: reduce` disables every transition longer than 100ms. No view animates by default at idle.
- **Print legibility.** Every viz prints in monochrome legibly. Categorical hues degrade to patterns under print, not flat grey.

---

## What 2.x viz already exists

Inventory of `site/explore.html` (tag `v2.1.0`):

| 2.x view | 3.0 relationship |
|----------|------------------|
| Overview tab: stacked decade histogram + beeswarm timeline | Adds alongside viz #1; the existing renderer remains the default until M4 ships a group-aware mode. Not removed. |
| Overview tab: faceted filter panel + word grid | Untouched; the filter chip vocabulary grows in M4/M5/M6/M7 as new facets land (group, region, platform, framing). |
| Triggers tab: trigger-events timeline | Feeds the chronicle band of viz #1. Tab remains as its own entry point. |
| Word detail tab: sense timeline + force graph | The sense timeline is what viz #1 extends; the force graph is the seed for viz #4. The 2.x sense timeline is *not removed in M4*; viz #2 is added alongside it. |
| Word detail tab: causal-hypothesis dashboard | Untouched. Will gain the fragmentation-index sparkline (#3) as a top strip in M3, leaving the dashboard intact below. |
| Compare tab | Stays. Cross-word comparison is orthogonal to multi-group expansion. |
| Network tab | Stays; potential merge with viz #4 at M-post-8, decided then. |
| Map tab (currently a placeholder plugin) | Replaced by viz #6 at M5. This is the only "replaces" relationship in M0–M8. |
| Trends tab | Stays. |
| Lexical loss tab | Direct precursor to viz #10; the loss tab is *promoted* to the cemetery view at M8 and gains the archival typography. The data already there flows in. |

Default policy through M4–M5: **adds alongside**. Nothing in 2.x is removed during those milestones. Replacement is only allowed when a 3.0 view strictly dominates the 2.x one *and* an ADR records the decision; this is the case only for the map tab at M5 (a placeholder, no user-facing regression) and for the lexical-loss tab at M8 (which is a promotion, not a removal).
