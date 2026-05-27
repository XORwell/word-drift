# ETL -- WORD-DRIFT

Ingest adapters that lift source datasets into the `drift:` ontology.
RML mappings live in `etl/rml/` (Trails); Python adapters fetch + normalise
source data, then either emit Turtle directly or feed RML.

## Adapters

| Script | Source | Produces | Status |
|--------|--------|----------|--------|
| `dwug_import.py` | DWUG DE + EN usage graphs | `drift:Word`, `drift:Sense` (clusters), `drift:attestedDuring` | DONE |
| `semeval_import.py` | SemEval-2020 Task 1 gold | `drift:DriftEvent` candidates (binary/graded change) | DONE |
| `dwds_freq.py` | DWDS Wortverlaufskurve | `drift:FrequencyObservation` | DONE |
| `wikidata_triggers.py` | Wikidata | `owl:sameAs` resolution + dates for `drift:TriggerEvent` | DONE |

## Running adapters

All adapters read from `etl/fixtures/` by default (small committed fixtures).
Each writes Turtle to `data/<name>.ttl` and prints `SHACL conforms=True`.

```bash
# Run all four adapters from the repo root:
python -u etl/dwug_import.py
python -u etl/semeval_import.py
python -u etl/dwds_freq.py
python -u etl/wikidata_triggers.py

# Combined triple count:
python -c "import rdflib,glob; g=rdflib.Graph(); [g.parse(f) for f in glob.glob('data/*.ttl')]; print(len(g),'triples in data/')"
```

## Real-download commands (run once, then cache under etl/.cache/)

Note: Zenodo record pages require login, but the Zenodo REST API content endpoint
delivers files without authentication. Use the API URLs below.

### DWUG German

```bash
# DWUG DE, Zenodo record 14028509, ~19 MB (CC-BY 4.0):
mkdir -p etl/.cache/
curl -L --max-time 300 \
  "https://zenodo.org/api/records/14028509/files/dwug_de.zip/content" \
  -o etl/.cache/dwug_de.zip
unzip etl/.cache/dwug_de.zip -d etl/.cache/dwug_de/

# Run real-data ingest (capped at 30 words):
python -u etl/dwug_import.py \
  --real-dir etl/.cache/dwug_de/dwug_de \
  --cap 30 \
  --output data/real/dwug_de.ttl

# Full uncapped ingest (all 50 words):
python -u etl/dwug_import.py \
  --real-dir etl/.cache/dwug_de/dwug_de \
  --cap 50 \
  --output data/real/dwug_de_full.ttl
```

Real layout:
- `data/<Word>/uses.csv` -- TAB-sep; columns: lemma, pos, date, grouping, identifier, ...
- `clusters/opt/<Word>.csv` -- TAB-sep; columns: identifier, cluster (-1 = noise, skipped)

### SemEval-2020 Task 1

```bash
# SemEval-2020 Task 1 post-eval release, Zenodo record 3931969, ~4 MB (CC-BY 4.0):
mkdir -p etl/.cache/
curl -L --max-time 120 \
  "https://zenodo.org/api/records/3931969/files/semeval2020_ulscd_posteval.zip/content" \
  -o etl/.cache/semeval2020_ulscd_posteval.zip
unzip etl/.cache/semeval2020_ulscd_posteval.zip -d etl/.cache/semeval2020/

# Run real-data ingest (all 37 English targets):
python -u etl/semeval_import.py \
  --real-dir etl/.cache/semeval2020/semeval2020_ulscd_posteval \
  --output data/real/semeval_en.ttl
```

Real layout:
- `test_data_truth/task1/english.txt` -- word_pos TAB 0|1, no header (binary change)
- `test_data_truth/task2/english.txt` -- word_pos TAB float, no header (graded change)
- word_pos format: e.g. `attack_nn`, `circle_vb` -- POS suffix kept in URI slug

### DWDS Wortverlaufskurve

```bash
# Bulk-download frequency curves per word (DWDS terms apply):
# https://www.dwds.de/r/plot?view=1&corpus=zeitungskorpus&q=<WORD>
# Cache one file per word, flatten to CSV, then:
python -u etl/dwds_freq.py etl/.cache/dwds_freq_full.csv
```

### Wikidata trigger events

```bash
# Static JSON fixture is the preferred approach (no live calls).
# For new trigger events: add entries to etl/fixtures/trigger_qids.json manually.
# See the commented _fetch_from_wikidata_sparql() function in wikidata_triggers.py
# for how a one-off enrichment SPARQL query would work against:
#   https://query.wikidata.org/sparql
```

## Real data triple counts (capped subset in data/real/)

| File | Words | SHACL | Triples |
|------|-------|-------|---------|
| `data/real/dwug_de.ttl` | 30 of 50 DWUG DE | conforms | 2646 |
| `data/real/semeval_en.ttl` | 37 of 37 SemEval EN | conforms | 760 |
| **combined** | | | **3406** |

Cap applied: DWUG DE limited to 30 words (alphabetically first 30 of 50) to keep the
committed Turtle under ~100 KB. Increase `--cap 50` to ingest all words.

## Conventions

- Cheapest path first: bulk-download + local parse over per-word API calls.
- Cache raw downloads under `etl/.cache/` (gitignored).
- Idempotent: re-running overwrites the generated `data/` Turtle, no dupes.
- Every generated node carries a `drift:hasSource` pointing at its `drift:Corpus`.
- Validate after every ingest: `python validate.py` (from repo root).
