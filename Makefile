# WORD-DRIFT — top-level convenience targets
# Usage:
#   make            # same as 'make all'
#   make validate   # run validate.py (SHACL + SPARQL eyeball pass)
#   make test       # run pytest suite
#   make etl-check  # smoke-test ETL adapters if any exist under etl/
#   make graph      # regenerate viz/data/graph.json + copy to site/
#   make serve      # serve the static site on :8080 (PORT=NNNN to override)
#   make all        # validate + test

.PHONY: all validate test etl-check graph serve metadata release lint-data stats check-qids coords export

all: validate test

PORT ?= 8080

graph:
	PYTHONUNBUFFERED=1 python viz/export.py
	cp viz/data/graph.json site/graph.json
	cp viz/data/graph-core.json site/graph-core.json
	cp viz/data/graph-detail.json site/graph-detail.json
	@echo "site/graph.json + graph-core.json + graph-detail.json refreshed"

serve:
	./scripts/serve.sh $(PORT)

validate:
	python validate.py

test:
	pytest

etl-check:
	@if ls etl/*.py 2>/dev/null | grep -q .; then \
	    echo "Running ETL adapters under etl/:"; \
	    for f in etl/*.py; do \
	        echo "  python $$f --dry-run 2>&1 | head -5"; \
	        python "$$f" --dry-run 2>&1 | head -5 || true; \
	    done; \
	else \
	    echo "No ETL adapters found in etl/ (skipping etl-check)."; \
	fi

stats:
	python scripts/stats.py

lint-data:
	python scripts/lint-data.py

# Regenerate the peer-review export artifacts into site/downloads/: the claims
# ledger (one auditable row per causal hypothesis with its sources), tabular
# CSVs, and the full dataset in Turtle / N-Triples / JSON-LD. Run after any data
# change so reviewers always get a current, citable snapshot.
export:
	python scripts/export-tables.py

# Regenerate the map's coordinate file from the current trigger owl:sameAs links
# (needs network: queries Wikidata). Run after any change to trigger QIDs so the
# map never plots a point for a removed/changed link.
coords:
	python scripts/fetch-trigger-coords.py

# Gate: every trigger owl:sameAs must resolve to a verified-OK Wikidata entity
# (no Wikimedia categories, disambiguation pages, deleted items, or type/label
# mismatches). Prevents wrong encyclopedia links from creeping back in.
check-qids:
	python scripts/audit-trigger-qids.py --check

# Regenerate the single-source-of-truth stats and point at the FAIR metadata.
metadata:
	@echo "Regenerating dataset statistics (single source of truth)..."
	python scripts/stats.py
	@echo ""
	@echo "FAIR / dataset metadata lives in:"
	@echo "  dataset-metadata/void.ttl        VoID dataset description (Turtle)"
	@echo "  dataset-metadata/dcat.ttl        DCAT dataset + distributions (Turtle)"
	@echo "  dataset-metadata/croissant.jsonld ML Commons Croissant (JSON-LD)"
	@echo "  docs/data-card.md                dataset data card"
	@echo "  .zenodo.json                     Zenodo deposition metadata (PREPARED)"
	@echo "  w3id/                            w3id.org redirect config (PREPARED)"
	@echo ""
	@echo "Counts come from data/reports/stats.json — never hand-typed."

# Full quality gate + frozen-release checklist. Does NOT publish anything.
release: validate test lint-data check-qids stats
	@echo ""
	@echo "All quality gates passed (validate + test + lint-data + stats)."
	@echo ""
	@echo "Frozen-release steps (MANUAL — require explicit user permission):"
	@echo "  1. Bump version in CITATION.cff, .zenodo.json, dataset-metadata/croissant.jsonld."
	@echo "  2. Update dcterms:modified in void.ttl + dcat.ttl to today."
	@echo "  3. git tag -s vX.Y.Z && push the tag to github.com."
	@echo "  4. Build the frozen archive; record its sha256 into croissant.jsonld."
	@echo "  5. Zenodo: upload archive with .zenodo.json -> mint DOI."
	@echo "     -> requires user go-ahead (NO auto-publish)."
	@echo "  6. w3id: open the PR per w3id/README.md to make IRIs resolve."
	@echo "     -> requires user go-ahead (NO auto-submit)."
	@echo ""
	@echo "NOTHING is published by this target."
