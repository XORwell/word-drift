# 04 — Data sources

This document inventories every source that 3.0 could plausibly draw on, says which dimension of the 3.0 model (group / geography / platform / emotion / memetic) each one actually contributes to, sketches an ingestion approach for the four that matter first, and is explicit about what is *not* going into the KG and why.

The guiding constraint, from `00-vision.md §6` and §7, is that every machine-derived attribution must be reproducible from a declared source + model + version. That is a stronger constraint than "we have a citation"; it rules out sources we cannot re-fetch, cannot re-annotate, or cannot re-attribute to a stable corpus span.

---

## 1. Inventory

| Source | Modality | Languages | Time span | Size (order of mag) | License | Ingest status |
|--------|----------|-----------|-----------|---------------------|---------|---------------|
| DWUG DE (`etl/.cache/dwug_de/`) | academic / mixed-genre diachronic | de | ~1800–2010 (2 bins) | ~50 target lemmas, 100k+ usages | CC BY 4.0 | cached, partially modelled (2.x drift events) |
| DWUG EN (`etl/.cache/dwug_en/`) | academic / mixed-genre diachronic | en | ~1810–2010 (2 bins) | ~40 lemmas | CC BY 4.0 | cached, partially modelled |
| SemEval-2020 Task 1 ULSCD (`etl/.cache/semeval2020/`) | shared-task release (de/en/la/sv) | de, en, la, sv | varies per language | ~30 lemmas/lang | CC BY 4.0 (mostly) | cached, not modelled |
| DURel (`etl/.cache/durel/`) | dictionary-like usage pair annotation | de | 1800s–2000s | small (curated) | research-use | cached, not modelled |
| SURel (`etl/.cache/surel/`) | domain-shift annotation (general ↔ cooking) | de | synchronic | small | research-use | cached, not modelled |
| OWiD frequency series (`etl/.cache/owid/`, `freq/`) | dictionary frequency | de | ~1900–present | dozens of lemmas | OWiD terms | cached, partially modelled (drift:FrequencyObservation) |
| Histwords vectors (`etl/.cache/histwords/`) | diachronic embeddings | en (mostly) | 1800s–1990s | several pretrained slices | research-use | cached, derived signals only |
| GFDS Wörter des Jahres (`etl/.cache/gfds/`) | curated lexical news | de | 1971–present | ~250 entries | unclear, treated as fair-use citation | cached, partially modelled (trigger events) |
| DWDS API | dictionary + corpus snippets | de | 1600s–present | very large | DWDS terms (academic use OK; redistribution restricted) | candidate, not started |
| Wikipedia revisions (DE/EN dumps) | wiki | de, en (others later) | 2001–present | tens of TB across languages | CC BY-SA 4.0 | candidate, not started |
| German Bundestag plenary protocols | parliamentary | de | 1949–present | ~GB of XML | public domain (state work) | candidate, not started |
| Reddit (Pushshift archives where available; otherwise API) | forum / microblog hybrid | en (most), de (r/de) | 2005–present | TB-scale archive | Reddit ToS; redistribution restricted | candidate, ethically scoped |
| X / Twitter | microblog | many | 2006–present | very large | closed API, ToS hostile to research since 2024 | candidate, deprioritised |
| TikTok captions | video-caption | many | 2017–present | large | no clean research API; scraping ethically questionable | not pursued |
| YouTube comments | forum-like | many | 2005–present | very large | API has quotas; commenter identity sensitive | candidate, deprioritised |
| Historical dictionary editions (Duden, OED, …) | dictionary | de, en | 1880s–present | medium | copyright restricted | derived-statistics only |
| Academic paper corpora (OpenAlex / S2ORC subsets) | academic | mostly en | ~1950–present | large | varies | candidate, low priority for M0–M3 |
| Personal blogs (curated, archive.org snapshots) | blog | many | ~1999–present | medium | varies; treat as cited rather than archived | candidate, low priority |

"Ingest status" is honest: cached means the bytes are on disk; modelled means we already lift them into the KG; partially modelled means some signal (e.g. frequency) is lifted but the source's full structure is not.

## 2. Source × dimension matrix

Columns are the 3.0 dimensions defined in `00-vision.md §2`. A cell is filled when the source can *plausibly* contribute that dimension, not merely overlap with it.

| Source | Group | Geography | Platform | Emotion | Memetic |
|--------|:-----:|:---------:|:--------:|:-------:|:-------:|
| DWUG DE / EN | (period bin only) | weak (corpus origin) | n/a | n/a | n/a |
| SemEval-2020 ULSCD | (period bin only) | weak | n/a | n/a | n/a |
| DURel / SURel | n/a / domain | n/a | n/a | n/a | n/a |
| OWiD frequency | n/a | n/a | n/a | n/a | n/a |
| GFDS Wörter des Jahres | curatorial group | DE | press / discourse | weak (curator framing) | yes (the award itself is memetic crystallisation) |
| Wikipedia revisions | editor community as group | language-edition geography | one Platform (Wikipedia) | weak — neutral-POV norm suppresses framing | strong (revision-level consensus shift, edit wars) |
| Bundestag protocols | speaker / party / fraktion | Germany, federal | one Platform (parliament) | moderate (rhetorical framing, polemic) | weak |
| Reddit (where ingest is legal) | subreddit community | weak (some geo subs) | yes (Reddit) | strong (voting + sentiment cues) | strong (memes, copypastas, irony) |
| X / Twitter (if accessible) | followed-account communities | weak | yes | strong | strong |
| Academic paper corpora | research community | weak | one Platform (publication) | very weak | weak |
| Personal blogs | individual / subculture | weak | yes (each blog is its own micro-platform) | strong | moderate |

Read this matrix as a planning aid: a column with only one strong source is a column where claims are going to depend heavily on that one source's biases. Emotion and Memetic both have that property; geography and group have several sources and are more robust.

## 3. Ingestion approach for the top four

Each pipeline lands in `etl/`. RML mappings live in `etl/rml/` (already on disk). SHACL shapes that gate the output live in `shapes/`.

### 3.1 DWUG DE / EN

- **Raw format.** Per-lemma directory tree: `data/<lemma>/uses.tsv`, `judgments.tsv`, `clusters/opt/<lemma>.csv`, `stats/`.
- **ETL.** Python loader walks the lemma tree; emits one `drift:Sense` per opt-cluster, one `drift:MeaningAttribution` per (cluster, period-bin) cell with weight = relative cluster mass. Annotator IDs become opaque `prov:Agent` identifiers; *no* annotator demographics are imported.
- **KG shape.** `Word → ontolex:sense → Sense`; each `Sense` carries `drift:MeaningAttribution` instances for the two DWUG period bins; each attribution has `prov:wasDerivedFrom` pointing at the DWUG release IRI and the lemma directory.
- **RML.** `etl/rml/dwug.ttl` (planned) maps `uses.tsv` rows to `prov:Activity` and `judgments.tsv` rows to evidence nodes attached to the attribution.
- **SHACL.** Every DWUG-derived `MeaningAttribution` must have exactly one period bin, at least one judgment-evidence node, and a `prov:wasDerivedFrom` pointing inside the DWUG release.

### 3.2 Wikipedia revisions

- **Raw format.** XML dump per language edition; `pages-meta-history.xml.bz2` for full revision history, `pages-articles.xml.bz2` for current text.
- **ETL.** Two stages: (a) extract a target-word index from article titles + redirects; (b) for each target, walk revisions, diff section-level changes, emit one `drift:MeaningAttribution` per revision-bin (monthly buckets) where the editor-community is the *group* and the language edition is a coarse *geography*.
- **KG shape.** `Word → Sense → MeaningAttribution(timeBin, editorCommunity, languageEdition)` with `drift:hasEvidence` pointing at a stable revision IRI (`<https://de.wikipedia.org/?oldid=...>`).
- **RML.** `etl/rml/wikipedia.ttl` (planned). RML is sufficient for the per-revision shape; section diffing happens in pre-RML Python.
- **SHACL.** Every Wikipedia-derived attribution requires a revision oldid (not just an article URL) and a language tag.

### 3.3 Bundestag plenary protocols

- **Raw format.** Open XML per session (`https://www.bundestag.de/services/opendata`).
- **ETL.** Walk session XML; speakers are already first-class XML elements with name, party (`fraktion`), and role. Tokenise speech turns; emit one `MeaningAttribution` per (target word, speech turn) with the speaker's `fraktion` as a `drift:Group` and "Bundestag plenary" as the `drift:Platform`. Region = Germany, federal; sub-federal region defers to M5.
- **KG shape.** Speaker becomes a `prov:Agent`; the *party* (not the individual) is the group attribution by default, to avoid building per-person dossiers (see §4). The individual is recorded as the `prov:Agent` of the speech act but is not used as the group axis unless an analyst explicitly opts in for one historically significant speaker.
- **RML.** `etl/rml/bundestag.ttl` (planned).
- **SHACL.** Plenary attributions require both a session IRI and a Fraktion. Individuals' utterances are stored but cross-referenceable only via the session IRI, not via a per-person index.

### 3.4 Reddit (or comparable forum corpus)

- **Raw format.** Pushshift-style monthly JSONL dumps for the historical window; live API for recent content where ToS permits research access.
- **ETL.** For each target word, sample posts/comments per subreddit per month; emit `MeaningAttribution` per (word, subreddit, month) with the subreddit as the `drift:CorpusContext`, Reddit as the `drift:Platform`, and aggregate vote signals as a weak evidence weight on emotional framing.
- **KG shape.** Per-comment identifiers are *not* stored as IRIs in the public KG. The stored evidence is the aggregate over a (subreddit, month, word) cell, plus a count of underlying comments. The raw comment table stays in a private staging store referenced only by hash.
- **RML.** `etl/rml/reddit.ttl` (planned), operating on the aggregate cells, not raw comments.
- **SHACL.** Reddit-derived attributions require a subreddit, a month bin, an aggregate-evidence count, and a non-empty hash of the underlying staging cell.

## 4. Licensing and ethics

The honest reading per source class:

- **DWUG, SemEval, DURel, SURel.** CC BY / research-use licences cover the annotations themselves. Reuse for an academic KG is fine. The KG re-emits the annotations under the same licence and credits the original releases at the dataset level.
- **OWiD, GFDS, dictionary editions.** Frequency series and dictionary signals are stored as *derived statistics* (counts, deltas, year labels), not as reproductions of dictionary text. Citation goes to the edition, not a fair-use snippet.
- **Wikipedia.** CC BY-SA 4.0 lets us republish revision-derived statistics and even revision text if needed, *if* we attribute correctly and propagate the share-alike. We do not republish article text in the KG; we emit revision-pointer IRIs.
- **Bundestag.** Plenary protocols are state work, effectively public domain. Individual speakers are public figures performing public office; their utterances in plenary are quotable. We still aggregate to the Fraktion level by default (see §3.3) because per-person utterance dossiers are not the research question, and building one as a side effect would be a misuse of the data.
- **Reddit / forum data.** Pushshift archives have been a research norm; Reddit's 2023+ position has tightened. We store *aggregates over a (subreddit, month, word) cell*, not per-user content, and we do not publish raw user content under any user's IRI. Username-keyed analysis is out of scope for the public KG.
- **X / Twitter.** Closed since 2024 for any volume that matters; we record the dimension as covered-in-principle but do not bet ingestion plans on access.
- **TikTok / closed platforms.** No clean research API; scraping at any volume is a ToS violation and ethically questionable on user-content grounds; we will not pursue it.

Across all sources, §6 of `00-vision.md` is binding: every attribution in the KG must be reproducible from declared source + model + version. That rules out any source where we cannot re-fetch the exact span (or its hash) that grounded the attribution. Dead-link-as-evidence is treated as missing evidence, not weak evidence.

## 5. What we will NOT ingest

- **Closed DM and private group archives** of any kind, including leaked corpora. Even with a public dump available, the participants did not write for a public KG.
- **Scraped paywalled news.** Article URLs as citations are fine; copying body text is not. Frequency series from a publisher's own API are fine when offered.
- **Deanonymised user content.** No per-username trajectory of meaning attribution gets published. Aggregates over communities are the unit.
- **Demographic inference about annotators or authors** (age, gender, ethnicity, political orientation derived from text). When annotators self-declare a category to the source release, we may carry it through; we do not infer it.
- **Health, sexual orientation, religion, or other GDPR Art. 9 categories** as group axes. The group dimension is communities and platforms, not individuals' protected characteristics.
- **Real-time social-media monitoring streams.** Per `00-vision.md §7`, the KG is a research instrument, not a monitoring product.

## 6. Cost notes

Local-first cost discipline (per workspace `CLAUDE.md`):

- **Free bulk.** Wikipedia dumps, Bundestag XML, DWUG / SemEval / DURel / SURel / OWiD, OpenAlex metadata. No API budget required. These are the M0–M4 backbone.
- **Free with friction.** Reddit historical archives (where still distributable), Wikipedia revision diffs at scale (CPU-bound, not API-bound), academic paper full-text via legal aggregators (some require institutional access).
- **API budget required.** Reddit live API where research access is granted (rate-limited; small monthly budget if any), DWDS API (free for academic use but rate-limited), and any LLM-assisted annotation work.
- **LLM strategy.** Per workspace policy and `00-vision.md §7`, bulk annotation work (sense clustering hints, framing pre-tags, candidate group labels) runs on local Ollama models (phi4 for validation, qwen3:8b for bulk, qwen3:14b for code-adjacent tasks). Anthropic API is reserved for hard cases: literary German, ambiguous political framing, and adjudication of disagreements between local models. Every LLM-derived attribution carries model name + version + prompt hash; without those, it does not make it past SHACL.
- **No paid corpus subscriptions** in scope for M0–M4. Re-evaluated at M5 if the geography dimension needs a paid regional press corpus.

A useful sanity check across this document: the dimensions where 3.0 actually has cheap, defensible data right now are *group* (parties in Bundestag, communities on Wikipedia + Reddit) and *time* (every source). *Geography* and *emotion* are thinner; *memetic* leans hard on one source class (forums). The milestones in `05-milestones.md` are ordered accordingly.
