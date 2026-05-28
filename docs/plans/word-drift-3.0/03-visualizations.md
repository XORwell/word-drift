# 03 — Visualisations

> A visualisation in word-drift is an instrument, not a dashboard. If a chart could carry the logo of a SaaS company without anyone noticing, it is the wrong chart.

Scope: the ten target views from the MASTER PROMPT, ordered from "extension of 2.x" to "new ground". Each spec is implementable in isolation. Cross-refs: `01-ontology-delta.md` (data shapes), `02-metrics.md` (derived quantities), `05-milestones.md` (when it ships).

Design language (binding, from `00-vision.md §5`): linguistic atlases, scientific observatories, museum archives, historical cartography, systems diagrams, editorial infographics, dark academia, semantic archaeology. References: *Sprachatlas des Deutschen Reichs*, Minard's flow maps, Tufte small multiples, NYT archival reconstructions, *TLS* timelines. Out: startup dashboards, crypto aesthetics, AI gradients, gamification, emoji-as-UI.

---

## 1. Semantic Drift Timeline (with historical overlay)

**Tagline.** One word's sense trajectory across centuries, anchored to the historical events that may have shaped it.

**What it shows.** Which senses were attested when, with which connotation, and which trigger events plausibly explain each shift.

**Data needed.** `senses[]`, `driftEvents[]`, `frequencyObservations[]`, `triggers[]` (2.x, in `graph-detail.json` + `graph-core.json`). New in 3.0: `drift:occurredInGroup` on drift events (`01-ontology-delta.md → group module`) so the timeline can split into per-group strands.

**Visual idiom.** Horizontal time axis, log-warped before 1800, linear after (historical-linguistic convention). Senses are *attestation bands* (intervals), not lines; vertical opacity = confidence. Drift events are arrowheads landing where the new sense begins. Below: a ruled *chronicle band* of triggers, with thin connectors reaching up to the drift arrows they hypothesise about. Bands beat lines because attestation is an interval phenomenon — a line falsely implies single-year precision the sources do not have.

**Interactions.** Hover band: gloss, source, evidence rung. Hover trigger: chronicle entry + affected words. Click trigger: filter chronicle to that category. Brush date range: zoom. Toggle "show cause links" (carried from 2.x).

**Status.** Extends 2.x word-detail timeline; lives alongside through M3; per-group split lands in **M4**.

**Aesthetic notes.** Ink-on-parchment for the chronicle band (warm neutral background, near-black lines). Three-step *cool* connotation ramp (blue-grey → grey → ochre-grey), explicitly not green/grey/red. Sense bands: darker stroke, 30% fill. Chronicle labels in italic serif.

**Must NOT.** Draw a single line through senses (imposes one trajectory). Colour positive green or negative red. Present chronicle connectors as causal proof — they are hypotheses, labelled with the 2.x evidence rung.

---

## 2. Meaning Distribution Graph

**Tagline.** Sense proportions over time, with majority and minority strands made explicit.

**What it shows.** How shares of competing senses move against each other. *"When did sense B overtake sense A, and how steep was the cross-over?"*

**Data needed.** `drift:MeaningAttribution` keyed by `(sense, time-bucket, group?)` with `drift:weight` and a CI (`01-ontology-delta.md → group + distribution modules`). Aggregated per word into `/graph-distribution.json` (new endpoint, M4). Falls back to a single series when no group attributions exist.

**Visual idiom.** Stacked area on a normalised 0–1 y-axis with a *hatched minority floor*: anything below 5% renders as a diagonal-line pattern rather than a solid fill, so marginalised senses stay visible without being inflated. CIs appear as lighter bands at each stratum's top edge. Optional small-multiples mode: one stack per group at identical scale. Small multiples beat stack-of-stacks (the latter is unreadable).

**Interactions.** Hover stratum: gloss, share, CI, top three citations. Click: pin; others fade to 30%. Toggle small-multiples vs single stack. Brush time range: emits a global filter to coordinated views.

**Status.** **M4.** Load-bearing artefact of that milestone.

**Aesthetic notes.** Categorical palette, one stable hue per sense IRI across all views, max six hues; overflow collapses to "other senses". CI bands at 40% of stratum hue, never grey. Hatching at 45°, 1 px stroke. ColorBrewer "Set2" or equivalent colour-blind-safe categorical.

**Must NOT.** Pick a "winning" sense via bold label or arrow. Hide the minority floor by clipping. Animate the stack rebuilding on load — research instrument, not reveal sequence.

---

## 3. Semantic Fragmentation Index

**Tagline.** A single number, per word, per moment: how fractured is the meaning.

**What it shows.** Trajectory of `semantic_fragmentation_index` (`02-metrics.md`) + glanceable current-state badge. *"Is this word coherent today, or pulling itself apart?"*

**Data needed.** Precomputed index per word per time-bucket (depends on `drift:MeaningAttribution` weights). Metric REST endpoint lands in M3.

**Visual idiom.** Sparkline (50–80 px tall) from earliest attestation to today, bold tick at the present value, discrete categorical badge ("coherent" / "drifting" / "fragmenting" / "fractured") from thresholds in `02-metrics.md`. Sits at the *top* of word-detail as a status strip, not a chart panel. Tufte "one number with context" — anything larger over-claims.

**Interactions.** Hover: year-by-year value + which group contributed most. Click badge: glossary entry with thresholds + formula.

**Status.** **M3** (initial plot on word detail); refined in **M4** when group splits land.

**Aesthetic notes.** Monochrome. Sparkline in body-text colour; current-value tick in the site's `--accent`. Badge set in small-caps body font, no fill.

**Must NOT.** Use a gauge, dial, or speedometer. Assign positive/negative valence to fragmentation — a word can be fractured for excellent reasons; the index is descriptive.

---

## 4. Semantic Constellation Map

**Tagline.** A word's neighbourhood: which senses sit near which, and which words occupy adjacent space.

**What it shows.** Topology of a word's senses and its semantic neighbours, projected to 2D. Clusters appear as constellations; overlaps as shared edges or bridge nodes.

**Data needed.** Sense embeddings per `drift:Sense` from a declared model + version (`ADR-0004`). `drift:relatedSense` and `drift:senseSibling` cross-refs (2.x cross-lingual siblings exist). Group attributions tint clusters.

**Visual idiom.** Force-directed graph: sense nodes (filled discs), word nodes (outlined discs), edges thresholded by embedding similarity (no hairball). Translucent *convex hulls* group related senses — the constellation. Edge thickness = similarity, node size = attestation frequency. **Layout computed once and stored**, not recomputed per load: the same word renders identically every time (reproducibility over animation).

**Interactions.** Hover node: gloss + attestation interval + group attributions. Click: re-centre (recomputed once, cached). Lasso a region: pin a focus group; coordinated views filter. Toggle "show bridges": highlight senses sitting on two hulls.

**Status.** Unscheduled (post-M8 candidate; needs the embedding-provenance contract).

**Aesthetic notes.** Dark-academia palette: deep navy or near-black background, ivory nodes, hull fills at 15% in a muted six-colour scheme. Labels in serif; small caps for words, italic lowercase for sense glosses. No glow.

**Must NOT.** Animate on idle ("breathing" graphs are dashboard kitsch). Use a starfield background. Produce a new layout on every reload.

---

## 5. Semantic Civil War View

**Tagline.** When a word splits into incompatible readings, this view holds both on the page without picking a side.

**What it shows.** Two (or more) group-conditioned readings of the same word, the evidence each cites, and when the bifurcation hardened.

**Data needed.** `drift:MeaningAttribution` grouped by `drift:Community` (`01-ontology-delta.md → group module`). `group_divergence` (`02-metrics.md`). Top-N exemplar corpus spans per group with provenance. Bifurcation date from divergence-velocity.

**Visual idiom.** Mirrored axis (Sankey-like split). Y-axis is time, descending; the word runs as a vertical spine down the centre. To either side, each group's dominant sense at each moment is a horizontal bar whose width is that sense's share *within that group*. Between spine and side: small-caps exemplar attestations per decade. When divergence-velocity flags a bifurcation, a horizontal *fault line* is drawn across both sides at that y-coordinate. Fault-line metaphor borrowed from stratigraphy — the correct register for a hardening disagreement.

**Interactions.** Hover bar: gloss + CI. Click exemplar: open source citation. Toggle "show neutral middle": attributions resisting group assignment appear in a centre column. Degrades cleanly with >2 groups.

**Status.** Unscheduled (needs M4 + a richer taxonomy than M2 will land).

**Aesthetic notes.** Diverging palette where the *axis is similarity-to-historical-baseline*, never moral valence. Sides: cool slate vs warm ochre. Fault line shares the fragmentation-badge accent.

**Must NOT.** Label sides with moral terms ("extremist", "mainstream", "rational"). Sides carry the literal KG group label and nothing else. Use red and blue (politically coded). Animate the bifurcation dramatically.

---

## 6. Geographic Semantic Maps

**Tagline.** The same word in different countries can mean substantially different things.

**What it shows.** Region-conditioned dominant sense + a secondary layer for local divergence intensity. *"Where does this word mean what?"*

**Data needed.** `drift:Region` (`01-ontology-delta.md → geography module`, M5). Region-conditioned `drift:MeaningAttribution`. Country boundaries: Natural Earth low-res (public domain). M5 granularity is country-level; sub-national deferred.

**Visual idiom.** *Categorical choropleth* coloured by the region's dominant sense, plus an overlaid *proportional-symbol layer* sized by within-region semantic entropy. A region where one sense dominates 95% gets a flat fill and no symbol; a region where three senses share gets the same flat fill (its plurality) plus a prominent overlay signalling internal disagreement. Adapts the *Sprachatlas* idiom (one colour per region) with a modern entropy overlay. Choropleth alone hides intra-region disagreement; symbols alone hide what people there actually mean.

**Interactions.** Hover: distribution + CI. Click: drill into the meaning-distribution graph filtered to that region. Projection toggle: Eckert IV default (equal-area), Mercator on request. Date slider: per-decade snapshots.

**Status.** **M5.**

**Aesthetic notes.** Categorical palette identical to the meaning-distribution palette — a sense is the same colour everywhere. Symbol overlay monochrome (accent), discrete five-step scale, not continuous. Colour-blind-safe categorical (ColorBrewer "Dark2"/"Set2"). Borders 0.5 px; data fills dominant.

**Must NOT.** Default to Mercator (inflates the global north). Extrapolate to regions with no attributions — missing data renders as neutral cross-hatch, not as "neutral meaning" or "absent meaning".

---

## 7. Platform Semantic Divergence

**Tagline.** A word on Reddit is not the same word in *Die Zeit*. This view holds the difference under a microscope.

**What it shows.** Sense distribution across platforms (Reddit, TikTok comments, newspaper corpora, academic prose, parliamentary speech) and how fast new senses leak across.

**Data needed.** `drift:Platform`, `drift:CorpusContext`, `drift:Register` (`01-ontology-delta.md → platform module`, M6). Platform-conditioned `drift:MeaningAttribution`. Cross-platform semantic-distance metric (`02-metrics.md`).

**Visual idiom.** *Bumps chart* (slope graph): one column per platform on the x-axis, one row per sense, sense-share encoded as band height in each column. Bands cross when shares flip between platforms. Time slider scrubs years. Above the bumps: a *velocity arrow strip* showing direction of share movement between adjacent platforms at the current year (e.g. "Reddit → mainstream press, lagging by 14 months"). Bumps are the canonical rank-and-share idiom; the velocity strip turns static comparison into the dynamic story.

**Interactions.** Hover band: platform-specific gloss + top exemplar. Click column header: filter coordinated views to that platform. Time slider continuous. Toggle "show lag arrows" — opt-in, to avoid clutter.

**Status.** **M6.**

**Aesthetic notes.** Same sense-hue palette as #2 and #6 (sense identity preserved across views). Platform columns are typographic, not iconographic — no platform logos, no platform brand colours. Plain italic labels.

**Must NOT.** Use platform brand colours. Display platform icons or logos. Editorialise platforms as "high-quality" or "low-quality" sources.

---

## 8. Emotional Semantic Heatmap

**Tagline.** Emotional loading of a word over time, decomposed into named affective dimensions.

**What it shows.** Heatmap of emotional framings (fear, irony, hostility, admiration, neutrality, …) across time, optionally split by group. *"When did this word turn ironic? When did it turn hostile? Did its denotation move, or just its affect?"*

**Data needed.** `drift:EmotionalFraming` with `drift:framingType`, `drift:valence`, `drift:loading` (`01-ontology-delta.md → emotion module`, M7). Every framing carries evidence (corpus span or model output with declared model + version + prompt — `ADR-0004`).

**Visual idiom.** *Small-multiples heatmap grid*: one row per framing dimension, x-axis = time, cell colour = loading intensity (sequential single-hue ramp per dimension), cell *saturation* = evidence strength. Adjacent: a parallel sparkline of denotation movement (sense-distribution change rate) on the same time scale, so the eye can compare "did meaning move?" vs "did affect move?". Without that companion the heatmap risks implying emotion *is* meaning.

**Interactions.** Hover cell: framing type, year-bucket, loading, top exemplar with model + version stamp. Click row: pin; others fade. Toggle "split by group": each row splits into per-group sub-rows. Filter by evidence rung (corpus-only, hide model-only).

**Status.** **M7.**

**Aesthetic notes.** Each framing dimension gets its own *sequential* hue ramp (ColorBrewer "YlOrBr" for hostility, "PuBu" for admiration, neutral grey for neutrality). Sequential, not diverging — emotional loading is intensity, not polarity. Saturation encodes evidence strength so low-evidence cells correctly look faded.

**Must NOT.** Collapse all emotions into a single "sentiment" score (sentiment is a denuded dimension; this view exists to recover the lost dimensions). Assert framings without showing the evidence rung per cell. Present model-derived framings indistinguishably from corpus-attested ones.

---

## 9. Memetic Mutation Timeline

**Tagline.** How a word travelled through internet culture: ironic appropriation, copypasta crystallisation, in-group signal collapse.

**What it shows.** Discrete memetic mutation events that transformed a word's meaning online, with the mutation mechanism named explicitly.

**Data needed.** `drift:MemeticMutation` subtypes of `drift:DriftEvent` (`01-ontology-delta.md → memetic module`, M8): `drift:IronicAppropriation`, `drift:CopypastaCrystallisation`, `drift:InGroupSignalCollapse`, `drift:AlgorithmicAmplification`. Per-event provenance (thread, platform, date, exemplar).

**Visual idiom.** Vertical *event ribbon* (timeline reads top-to-bottom — the editorial long-read convention). Each mutation is a horizontal card pinned to its date with: mechanism (italic label), one-sentence editorial gloss, exemplar quote, arrow to next event. Right margin: a continuous fragmentation-index sparkline at the same date scale, so the reader sees whether each mutation made the word more or less coherent overall. Cards-with-arrows are honest about discreteness; a smooth chart would falsely smooth a stepwise phenomenon.

**Interactions.** Hover card: full provenance (thread URL if licensed, otherwise date + platform + screenshot description). Click mechanism label: filter ribbon to that mechanism class across corpus. Date jump: anchor links per decade.

**Status.** **M8.**

**Aesthetic notes.** Editorial typography: serif body, small-caps mechanism labels, generous leading. Card background = chronicle-band parchment from #1. Mechanism labels distinguished *typographically*, not by colour (no natural ordering of mutation mechanisms). Exemplars in a monospaced face to mark them as quoted material.

**Must NOT.** Embed animated GIFs of the actual memes (legal, ethical, aesthetic). Editorialise memes as "good" or "bad" content. Omit the mutation mechanism — a memetic timeline without named mechanisms is just a list of dates.

---

## 10. Semantic Cemetery

**Tagline.** Words whose historically dominant meaning is now a minority reading: an archival register, not an elegy.

**What it shows.** A curated, filterable list of words whose dominant-historical sense now accounts for less than 5% of attributions, presented with the dignity of an archive entry.

**Data needed.** `drift:SemanticCemetery` SPARQL view (not a class) returning words where `historicalDominant.currentShare < 0.05` (`02-metrics.md`). Per entry: old sense (gloss, dominance interval, last attestation), current dominant sense, mediating mutation events.

**Visual idiom.** A *register* typographically modelled on a museum inventory or finding-aid index. Three-column card per entry: left = word as heading + old gloss in italic; centre = dominance interval ("dominant 1870–1968") + last firmly-attested year; right = current dominant sense with present share. A small horizontal *decline sparkline* across the card's bottom shows the old sense's share over time. The page reads as an archival index, not a graveyard.

**Interactions.** Filter by language, century-of-decline, mutation mechanism. Click entry: open word-detail with #1's timeline pre-scrolled to the dominance interval. Sort by current share, length of dominance, or recency of decline.

**Status.** **M8.**

**Aesthetic notes.** Strictly typographic. Single near-black ink on parchment background. No category colours. Sparkline in the same near-black, no fill. Reads as a printed index, not a web app.

**Must NOT.** Use funeral metaphors (tombstones, crosses, RIP, dates-in-parentheses styling). Romanticise meaning-loss as cultural decline — the register includes words whose receding meaning was harmful (slurs, propaganda terms); their decline is not a loss. Exclude words because their old meaning is unfashionable to mention.

---

## Cross-viz coordination

Coordinated views share state via a single in-page *selection bus* (small pub-sub, not a framework store). Three coordinated selections in M4, more per milestone:

- **Word selection.** Opening a word anywhere scrolls word-detail into focus and propagates the IRI to every word-aware view.
- **Time-range brush.** Brushing in #1, #2, or #3 emits `time:[from,to]`; #6, #7, #9 honour it as a soft filter.
- **Group selection.** Pinning a group in #2 or #5 emits `group:<id>`; #6, #7, #8 honour it softly; #6 hard-filters (regions without attributions render as missing-data hatch).

Selection is *transparent*: an "active filters" strip at the top lists every selection with x-to-remove (mirrors 2.x `#active-filters-bar`). No view consumes a filter silently.

```
[brush in #2: 1980–2010]
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
 #1 ok  #6 ok  #7 ok    (#4, #5, #10 ignore time)
```

---

## Frontend tech notes

The current site is plain HTML + JS with vendored D3 v7 and a small `WD.registerView()` plugin registry (`site/assets/views/API.md`). 3.0 stays inside this surface; introducing a framework is rejected by default.

**Default:** D3 v7 plus, where the chart type fits, **Observable Plot** loaded the same way (vendored, no build step). Plot is a 25 KB grammar-of-graphics layer over D3 giving small-multiples and faceting declaratively, degrading cleanly to raw D3 when something custom is needed.

| Viz | Tech |
|-----|------|
| 1. Drift timeline | D3 (extend 2.x renderer). |
| 2. Meaning distribution | Plot `area()` + faceting. |
| 3. Fragmentation index | Inline SVG sparkline, no library. |
| 4. Constellation map | D3 force layout; Canvas at >500 nodes, else SVG. |
| 5. Civil-war view | D3 (mirrored axis not in Plot's vocabulary). |
| 6. Geographic map | D3 + Natural Earth TopoJSON; Plot for legend small-multiples. |
| 7. Platform divergence | Plot bumps via `lineY({channels})`. |
| 8. Emotional heatmap | Plot `cell()` faceted by framing dimension. |
| 9. Memetic timeline | Plain HTML + CSS grid (editorial layout, not data viz). |
| 10. Semantic cemetery | HTML + CSS grid + inline SVG sparkline per entry. |

Canvas reserved for #4 above 500 nodes; everything else stays SVG for accessibility and screenshot fidelity. **No build step.** Vendor Plot's UMD into `site/assets/vendor/` next to D3.

**Door left open.** If a future view needs reactivity across many small components (the bus grows beyond ~5 views), re-evaluate with an ADR — likely Lit, never React. No SvelteKit, no Next.js, no router.

---

## Accessibility

Every viz must pass before its milestone is done:

- **Colour-blindness.** Categorical palettes ColorBrewer-derived and verified against deuteranopia + protanopia simulators. Diverging palettes (#5, #8) use blue/ochre or blue/orange, never red/green. Sequential palettes (#3, #7, #8) are single-hue.
- **Screen-reader story.** Each viz in a `<figure>` with a `<figcaption>` auto-generated from data ("Three senses share this word, dominant X at 62%, sense Y rising from 5% to 31% between 2010 and 2024."). Chart in `role="img"` with `aria-labelledby` pointing at the caption. Every chart has a "Show table" toggle exposing a data-table fallback.
- **Keyboard navigation.** Every hover target, brush handle, and toggle has a keyboard equivalent: arrows move between data points, Enter activates, Esc clears. Focus rings visible (existing 2 px style).
- **Reduced motion.** `prefers-reduced-motion: reduce` disables every transition >100 ms. No view animates by default at idle.
- **Print legibility.** Every viz prints in monochrome legibly. Categorical hues degrade to patterns under print, not flat grey.

---

## What 2.x viz already exists

Inventory of `site/explore.html` (tag `v2.1.0`):

| 2.x view | 3.0 relationship |
|----------|------------------|
| Overview: stacked decade histogram + beeswarm timeline | Adds-alongside #1; existing renderer is default until M4 ships a group-aware mode. Not removed. |
| Overview: faceted filter panel + word grid | Untouched; chip vocabulary grows in M4/M5/M6/M7 (group, region, platform, framing). |
| Triggers tab | Feeds the chronicle band of #1. Tab remains its own entry point. |
| Word detail: sense timeline + force graph | Sense timeline is what #1 extends; force graph seeds #4. Sense timeline is *not removed in M4*; #2 is added alongside. |
| Word detail: causal-hypothesis dashboard | Untouched. Gains the fragmentation sparkline (#3) as a top strip in M3, leaving the dashboard intact below. |
| Compare tab | Stays. Orthogonal to multi-group. |
| Network tab | Stays; possible merge with #4 post-M8, decided then. |
| Map tab (placeholder plugin) | Replaced by #6 at M5. The only "replaces" in M0–M8 (no user-facing regression, placeholder only). |
| Trends tab | Stays. |
| Lexical loss tab | Direct precursor to #10; *promoted* at M8 into the cemetery view with archival typography. Data flows in. |

Default policy through M4–M5: **adds alongside**. Nothing in 2.x is removed during those milestones. Replacement requires the new view to strictly dominate the 2.x one *and* an ADR; this holds only for the map placeholder at M5 and the lexical-loss promotion at M8.
