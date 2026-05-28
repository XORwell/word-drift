# 04 — Data sources

This document inventories every source 3.0 could plausibly draw on, says which dimension of the 3.0 model (group / geography / platform / emotion / memetic) each one contributes to, sketches an ingestion approach for the four that matter first, and is explicit about what is *not* going into the KG.

The binding constraint, from `00-vision.md §6`, is that every machine-derived attribution must be reproducible from declared source + model + version. That rules out sources we cannot re-fetch, cannot re-annotate, or cannot re-attribute to a stable corpus span.

---

## 1. Inventory

| Source | Modality | Languages | Time span | Size | License | Ingest status |
|--------|----------|-----------|-----------|------|---------|---------------|
| DWUG DE (`etl/.cache/dwug_de/`) | academic / mixed-genre diachronic | de | ~1800–2010, 2 bins | ~50 lemmas | CC BY 4.0 | cached, partially modelled |
| DWUG EN (`etl/.cache/dwug_en/`) | academic / mixed-genre diachronic | en | ~1810–2010, 2 bins | ~40 lemmas | CC BY 4.0 | cached, partially modelled |
| SemEval-2020 ULSCD (`etl/.cache/semeval2020/`) | shared-task release | de, en, la, sv | varies | ~30 lemmas/lang | CC BY 4.0 (mostly) | cached, not modelled |
| DURel (`etl/.cache/durel/`) | usage-pair annotation | de | 1800s–2000s | small, curated | research-use | cached, not modelled |
| SURel (`etl/.cache/surel/`) | domain-shift annotation | de | synchronic | small | research-use | cached, not modelled |
| OWiD frequency (`etl/.cache/owid/`, `freq/`) | dictionary frequency | de | ~1900–present | dozens of lemmas | OWiD terms | cached, partially modelled |
| Histwords vectors (`etl/.cache/histwords/`) | diachronic embeddings | en (mostly) | 1800s–1990s | several slices | research-use | cached, derived signals only |
| GFDS Wörter des Jahres (`etl/.cache/gfds/`) | curated lexical news | de | 1971–present | ~250 entries | unclear; fair-use citation | cached, partially modelled |
| DWDS API | dictionary + corpus | de | 1600s–present | very large | DWDS terms (academic use OK, redist restricted) | candidate, not started |
| Wikipedia revisions (dumps) | wiki | de, en (others later) | 2001–present | TB-scale | CC BY-SA 4.0 | candidate, not started |
| Bundestag plenary protocols | parliamentary | de | 1949–present | ~GB of XML | public domain (state work) | candidate, not started |
| Reddit (Pushshift archives + API) | forum / microblog | en, de | 2005–present | TB-scale | ToS; redistribution restricted | candidate, ethically scoped |
| X / Twitter | microblog | many | 2006–present | very large | closed API since 2024 | candidate, deprioritised |
| TikTok captions | video-caption | many | 2017–present | large | no research API; scrape ethically dubious | not pursued |
| YouTube comments | forum-like | many | 2005–present | very large | API quotas; commenter identity sensitive | candidate, deprioritised |
| Historical dictionary editions (Duden, OED, …) | dictionary | de, en | 1880s–present | medium | copyright restricted | derived-statistics only |
| Academic paper corpora (OpenAlex / S2ORC subsets) | academic | mostly en | ~1950–present | large | varies | candidate, low priority |
| Personal blogs (archive.org snapshots) | blog | many | ~1999–present | medium | varies | candidate, low priority |

"Ingest status" is honest: *cached* means bytes are on disk; *modelled* means lifted into the KG; *partially modelled* means one signal (e.g. frequency) is lifted but not the full structure.

## 2. Source × dimension matrix

A cell is filled when the source can plausibly contribute that dimension, not merely overlap with it.

| Source | Group | Geography | Platform | Emotion | Memetic |
|--------|:-----:|:---------:|:--------:|:-------:|:-------:|
| DWUG DE / EN | (period only) | weak | n/a | n/a | n/a |
| SemEval-2020 ULSCD | (period only) | weak | n/a | n/a | n/a |
| DURel / SURel | n/a / domain | n/a | n/a | n/a | n/a |
| OWiD frequency | n/a | n/a | n/a | n/a | n/a |
| GFDS WdJ | curatorial | DE | press / discourse | weak | yes (award = crystallisation) |
| Wikipedia revisions | editor community | language edition | yes (Wikipedia) | weak (NPOV norm) | strong (consensus shift, edit wars) |
| Bundestag protocols | speaker / party / Fraktion | DE federal | yes (parliament) | moderate (rhetorical framing) | weak |
| Reddit | subreddit community | weak | yes (Reddit) | strong (votes + cues) | strong (memes, irony) |
| X / Twitter | followed-account communities | weak | yes | strong | strong |
| Academic paper corpora | research community | weak | yes (publication) | very weak | weak |
| Personal blogs | individual / subculture | weak | yes (each blog) | strong | moderate |

Columns with only one strong source carry that source's biases. Emotion and memetic both have that property; group and time are more robust. The milestones in `05-milestones.md` are ordered accordingly.

## 3. Ingestion approach for the top four

Pipelines land in `etl/`. RML mappings live in `etl/rml/`. SHACL shapes that gate the output live in `shapes/`.

### 3.1 DWUG DE / EN

- **Raw.** Per-lemma tree: `data/<lemma>/uses.tsv`, `judgments.tsv`, `clusters/opt/<lemma>.csv`.
- **ETL.** Walk lemma tree; emit one `drift:Sense` per opt-cluster, one `drift:MeaningAttribution` per (cluster, period-bin) with weight = relative cluster mass. Annotator IDs become opaque `prov:Agent`; no annotator demographics are imported.
- **KG shape.** `Word → ontolex:sense → Sense`; each `Sense` carries attributions for the two DWUG bins; each attribution has `prov:wasDerivedFrom` pointing at the DWUG release IRI.
- **RML.** `etl/rml/dwug.ttl` (planned) maps `uses.tsv` to `prov:Activity`, `judgments.tsv` to evidence nodes.
- **SHACL.** Each DWUG-derived attribution: exactly one period bin, ≥1 judgment-evidence node, `prov:wasDerivedFrom` inside the DWUG release.

### 3.2 Wikipedia revisions

- **Raw.** `pages-meta-history.xml.bz2` per language edition.
- **ETL.** Two stages: (a) build a target-word index from titles + redirects; (b) per target, walk revisions, diff section-level changes, emit one attribution per monthly revision-bin with editor-community as group and language edition as coarse geography.
- **KG shape.** Attribution carries `drift:hasEvidence` pointing at a stable revision IRI (`<https://de.wikipedia.org/?oldid=...>`).
- **RML.** `etl/rml/wikipedia.ttl` (planned); section diffing happens pre-RML in Python.
- **SHACL.** Every Wikipedia-derived attribution requires a revision oldid (not just an article URL) and a language tag.

### 3.3 Bundestag plenary protocols

- **Raw.** Open XML per session (`bundestag.de/services/opendata`); speakers, party (Fraktion), role already first-class.
- **ETL.** Walk session XML; tokenise speech turns; emit one attribution per (target word, speech turn) with Fraktion as `drift:Group` and "Bundestag plenary" as `drift:Platform`. Region = DE federal; sub-federal defers to M5.
- **KG shape.** Speaker is a `prov:Agent` of the speech act; the *party* is the group attribution by default, to avoid building per-person dossiers (see §4).
- **RML.** `etl/rml/bundestag.ttl` (planned).
- **SHACL.** Plenary attributions require both session IRI and Fraktion. Individuals' utterances are reachable via session IRI, not via a per-person index.

### 3.4 Reddit (or comparable forum corpus)

- **Raw.** Pushshift-style monthly JSONL for the historical window; live API for recent windows where ToS allows research use.
- **ETL.** Per target word, sample posts/comments per subreddit per month; emit attribution per (word, subreddit, month) with subreddit as `drift:CorpusContext`, Reddit as `drift:Platform`, aggregate vote signals as weak evidence for emotional framing.
- **KG shape.** Per-comment IDs are *not* stored as IRIs in the public KG. Stored evidence is the (subreddit, month, word) aggregate plus an underlying-comment count. Raw comment table stays in a private staging store referenced only by hash.
- **RML.** `etl/rml/reddit.ttl` (planned), operating on aggregate cells.
- **SHACL.** Reddit-derived attributions require subreddit, month bin, aggregate-evidence count, and a hash of the underlying staging cell.

## 4. Licensing and ethics

- **DWUG, SemEval, DURel, SURel.** CC BY / research-use covers reuse for an academic KG. The KG re-emits annotations under the same licence and credits the releases at dataset level.
- **OWiD, GFDS, dictionary editions.** Stored as *derived statistics* (counts, deltas, year labels), not as reproductions of dictionary text. Citation goes to the edition.
- **Wikipedia.** CC BY-SA 4.0 lets us republish revision-derived statistics with attribution and share-alike. We do not republish article text in the KG; we emit revision-pointer IRIs.
- **Bundestag.** Plenary protocols are state work, effectively public domain. Speakers are public figures performing public office; utterances in plenary are quotable. We still aggregate to Fraktion level by default (§3.3) because per-person utterance dossiers are not the research question and building one as a side effect would be a misuse.
- **Reddit / forum data.** Pushshift archives have been a research norm; Reddit's 2023+ position has tightened. We store aggregates over (subreddit, month, word), not per-user content, and we do not publish raw user content under any user's IRI. Username-keyed analysis is out of scope for the public KG.
- **X / Twitter.** Closed since 2024 for any meaningful volume; recorded as covered-in-principle, not bet on.
- **TikTok / closed platforms.** No clean research API; scraping is a ToS violation and ethically dubious on user-content grounds. Not pursued.

Across all sources, `00-vision.md §6` binds: dead-link-as-evidence is treated as missing evidence, not weak evidence.

## 5. What we will NOT ingest

- **Closed DM or private group archives**, even when leaked. Participants did not write for a public KG.
- **Scraped paywalled news.** Article URLs as citations are fine; copying body text is not. Publisher-offered frequency series are fine.
- **Deanonymised user content.** No per-username trajectory of meaning attribution gets published. Aggregates over communities are the unit.
- **Demographic inference about authors or annotators** (age, gender, ethnicity, political orientation derived from text). Self-declared categories may be carried through from the source release; we do not infer them.
- **GDPR Art. 9 categories as group axes** (health, sexual orientation, religion, …). The group dimension is communities and platforms, not individuals' protected characteristics.
- **Real-time social-media monitoring streams.** Per `00-vision.md §7`, the KG is a research instrument, not a monitoring product.

## 6. Cost notes

Local-first cost discipline (per workspace `CLAUDE.md`):

- **Free bulk.** Wikipedia dumps, Bundestag XML, DWUG / SemEval / DURel / SURel / OWiD, OpenAlex metadata. The M0–M4 backbone.
- **Free with friction.** Reddit historical archives where distributable, Wikipedia revision diffs at scale (CPU-bound, not API-bound), academic full-text via legal aggregators.
- **API budget.** Reddit live API where research access is granted (rate-limited, small monthly budget if any), DWDS API (free for academic use, rate-limited), and any LLM-assisted annotation.
- **LLM strategy.** Bulk annotation hints (sense clustering, framing pre-tags, candidate group labels) run on local Ollama models — phi4 for validation, qwen3:8b for bulk, qwen3:14b for code-adjacent tasks. Anthropic API is reserved for hard cases: literary German, ambiguous political framing, adjudication between local models. Every LLM-derived attribution carries model + version + prompt hash; without those, it fails SHACL.
- **No paid corpus subscriptions** in scope for M0–M4. Re-evaluated at M5 if geography needs a paid regional press corpus.

The dimensions where 3.0 has cheap, defensible data right now are *group* (parties in Bundestag, communities on Wikipedia + Reddit) and *time* (every source). *Geography* and *emotion* are thinner; *memetic* leans hard on one source class (forums).
