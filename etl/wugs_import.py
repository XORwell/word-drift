"""
wugs_import.py -- ETL adapter: full IMS Stuttgart WUG benchmark datasets -> drift:.

Ingests the DERIVED target-word + gold-change layer of four CC-BY-4.0 Word Usage
Graph datasets as a DETECTION-GRADE backbone (ADR 0004): broad coverage + German,
NOT causal claims. Raw usage graphs are never redistributed -- only one
drift:Word + a drift:DriftEvent carrying the dataset's gold drift:gradedChange.

Datasets + where the gold score lives:
  DWUG DE / DWUG EN  -- stats/opt/stats_groupings.csv columns
                        `change_binary` (0/1) + `change_graded` (JSD in [0,1]).
                        change_graded is used directly as drift:gradedChange.
  DURel / SURel      -- stats/stats_groupings.csv columns EARLIER / LATER /
                        COMPARE (mean DURel-scale usage relatedness, 1..4).
                        The DURel framework's graded-change measure is the drop
                        in cross-period relatedness: mean(EARLIER,LATER)-COMPARE,
                        normalised to [0,1] by dividing by the scale span (3).
                        Clamped to [0,1]. Documented, not invented.

Per ADR 0004: a benchmark word gets NO drift:CausalHypothesis. gradedChange is a
detection magnitude, not a causal confidence. Cause stays undetermined.

Dedup: target words already modelled (by lower-cased written form within the
same language) in data/dwug.ttl, data/semeval.ttl or examples/ are SKIPPED so no
duplicate Word IRIs / re-modelled words are emitted. IRIs are dataset-namespaced
(word-dwugde-, word-dwugen-, word-durel-, word-surel-) so they never collide with
the existing small-fixture word-dwug-* / word-semeval-* IRIs either.

ChangeSignalAlignment lift: for any ingested word that matches an EXISTING curated
word carrying a drift:CausalHypothesis, an alignment evidence stub is written to
data/alignment/wugs-change-signal.ttl referencing the existing wdr:hyp-* IRI
(adds drift:evidenceType drift:ChangeSignalAlignment + drift:hasSource only;
never re-types, re-confidences, or asserts a cause).

Usage:
  python -u etl/wugs_import.py            # build all four data/wugs/*.ttl + alignment
  python -u etl/wugs_import.py --report   # also print a per-dataset summary
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
from pathlib import Path

import rdflib
from rdflib import Literal
from rdflib.namespace import RDF

from _common import (
    DRIFT, WDR, ONTOLEX, DCT, RDFS, SKOS, XSD, PROV,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / ".cache"
OUT_DIR = ROOT / "data" / "wugs"
ALIGN_OUT = ROOT / "data" / "alignment" / "wugs-change-signal.ttl"

# DURel 1..4 relatedness scale span used to normalise the relatedness-drop to [0,1].
DUREL_SCALE_SPAN = 3.0

# Two-period anchors. DWUG/DURel/SURel each contrast an earlier vs a later corpus
# slice; the exact boundaries vary per dataset, so we use coarse century-level
# anchors purely as a timeline hook (the gold signal is the gradedChange, not the year).
PERIOD_ANCHORS = {
    # dataset -> (earlier_year, later_year, drift_year)
    "dwug_de": (1835, 1990, 1912),   # DTA (1800-1899) vs BZ/ND (1946-1990)
    "dwug_en": (1835, 1985, 1910),   # CCOHA 1810-1860 vs 1960-2010
    "durel":   (1750, 1900, 1825),   # DTA 18th c. vs 19th c. German
    "surel":   (1990, 2010, 2000),   # general vs cooking-domain (synchronic)
}

# Dataset registry: name -> (groupings_csv_relpath, language, source metadata, kind)
DATASETS = {
    "dwug_de": {
        "csv": "dwug_de/dwug_de/stats/opt/stats_groupings.csv",
        "lang": "de",
        "kind": "dwug",
        "label": "DWUG",
        "source_iri": "src-wugs-dwug-de",
        "title": "DWUG German (Diachronic Word Usage Graphs, Schlechtweg et al.)",
        "url": "https://zenodo.org/records/14028509",
        "doi": "10.5281/zenodo.5543723",
    },
    "dwug_en": {
        "csv": "dwug_en/dwug_en/stats/opt/stats_groupings.csv",
        "lang": "en",
        "kind": "dwug",
        "label": "DWUG",
        "source_iri": "src-wugs-dwug-en",
        "title": "DWUG English (Diachronic Word Usage Graphs, Schlechtweg et al.)",
        "url": "https://zenodo.org/records/14028531",
        "doi": "10.5281/zenodo.5544443",
    },
    "durel": {
        "csv": "durel/durel/stats/stats_groupings.csv",
        "lang": "de",
        "kind": "durel",
        "label": "DURel",
        "source_iri": "src-wugs-durel",
        "title": "DURel German (Diachronic Usage Relatedness, Schlechtweg et al.)",
        "url": "https://zenodo.org/records/5784453",
        "doi": "10.5281/zenodo.5541274",
    },
    "surel": {
        "csv": "surel/surel/stats/stats_groupings.csv",
        "lang": "de",
        "kind": "durel",  # same EARLIER/LATER/COMPARE layout
        "label": "SURel",
        "source_iri": "src-wugs-surel",
        "title": "SURel German (Synchronic Usage Relatedness, Schlechtweg et al.)",
        "url": "https://zenodo.org/records/5784569",
        "doi": "10.5281/zenodo.5543306",
    },
}

ALIGN_SOURCE_IRI = WDR["src-wugs-changesignal"]
ALIGN_AGENT_IRI = WDR["wugs-alignment-curator"]


# ---------------------------------------------------------------------------
# Dedup + curated-hypothesis context (built from the in-repo graph)
# ---------------------------------------------------------------------------

def _load_context() -> tuple[dict, dict]:
    """
    Returns:
      existing_forms: {lang: set(lower writtenForm)} from data/dwug, data/semeval, examples/
      curated_hyps:   {(slug, lang): [hyp_local_name, ...]} for words carrying a CausalHypothesis
    """
    g = rdflib.Graph()
    files = sorted(glob.glob(str(ROOT / "examples" / "**" / "*.ttl"), recursive=True))
    for extra in ("data/dwug.ttl", "data/semeval.ttl"):
        p = ROOT / extra
        if p.exists():
            files.append(str(p))
    for f in files:
        g.parse(f, format="turtle")

    existing_forms: dict[str, set] = {}
    for w in g.subjects(RDF.type, DRIFT.Word):
        for wf in g.objects(w, DRIFT.writtenForm):
            lang = getattr(wf, "language", None) or ""
            existing_forms.setdefault(lang, set()).add(str(wf).lower())

    curated_hyps: dict[tuple[str, str], list[str]] = {}
    for hyp in g.subjects(RDF.type, DRIFT.CausalHypothesis):
        for de in g.objects(hyp, DRIFT.aboutDrift):
            for w in g.objects(de, DRIFT.affectsWord):
                for wf in g.objects(w, DRIFT.writtenForm):
                    lang = getattr(wf, "language", None) or ""
                    key = (slugify(str(wf)), lang)
                    curated_hyps.setdefault(key, [])
                    name = str(hyp).rsplit("/", 1)[-1]
                    if name not in curated_hyps[key]:
                        curated_hyps[key].append(name)
    return existing_forms, curated_hyps


# ---------------------------------------------------------------------------
# Gold-score extraction per dataset row
# ---------------------------------------------------------------------------

def _row_form_and_score(row: dict, lang: str, kind: str):
    """
    Return (written_form, slug_lemma, binary_change|None, graded_change) for one row.

    slug_lemma keeps any POS suffix (DWUG EN attack_nn) so the IRI is unique;
    written_form strips it for the human-facing label.
    """
    lemma = row["lemma"].strip()
    if lang == "en" and "_" in lemma:
        form = lemma.rsplit("_", 1)[0]
    else:
        form = lemma

    if kind == "dwug":
        binary = int(row["change_binary"]) if row.get("change_binary", "").strip() != "" else None
        graded = float(row["change_graded"])
    else:  # durel / surel: derive change from relatedness drop
        earlier = float(row["EARLIER"])
        later = float(row["LATER"])
        compare = float(row["COMPARE"])
        # Mean intra-period relatedness minus cross-period relatedness, normalised.
        raw = (earlier + later) / 2.0 - compare
        graded = raw / DUREL_SCALE_SPAN
        binary = None  # DURel/SURel ship no binary gold label

    graded = min(1.0, max(0.0, round(graded, 4)))
    return form, lemma, binary, graded


# ---------------------------------------------------------------------------
# TTL emission
# ---------------------------------------------------------------------------

def _add_source(g, meta: dict):
    src = WDR[meta["source_iri"]]
    g.add((src, RDF.type, DRIFT.Corpus))      # Corpus is a drift:Source subclass
    g.add((src, DCT.title, Literal(meta["title"], lang="en")))
    g.add((src, RDFS.label, Literal(meta["label"], lang="en")))
    g.add((src, DRIFT.sourceURL, Literal(meta["url"], datatype=XSD.anyURI)))
    g.add((src, DCT.identifier, Literal("doi:" + meta["doi"])))
    g.add((src, RDFS.comment, Literal(
        "Benchmark (gold human-annotated lexical semantic change). Ingested as "
        "detection-grade backbone: derived target-word + gold graded-change only, "
        "no raw usage graphs, no causal claim (ADR 0004).", lang="en")))
    return src


def build_dataset_graph(name: str, meta: dict, existing_forms: dict):
    """
    Build the TTL graph for one dataset. Returns (graph, ingested_words, skipped_words).
    ingested_words: list of (form, slug_lemma, binary, graded)
    skipped_words:  list of form (already modelled elsewhere)
    """
    csv_path = CACHE / meta["csv"]
    lang = meta["lang"]
    kind = meta["kind"]
    earlier_y, later_y, drift_y = PERIOD_ANCHORS[name]

    g = make_graph()
    src = _add_source(g, meta)

    have = existing_forms.get(lang, set())
    ingested, skipped = [], []
    # every row's gold score, keyed by slug, regardless of dedup -- the alignment
    # lift needs the benchmark score for curated words even when their Word node
    # is already modelled elsewhere (so they are deduped here).
    all_scores = []

    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            form, lemma, binary, graded = _row_form_and_score(row, lang, kind)
            all_scores.append((form, lemma, binary, graded))
            if form.lower() in have:
                skipped.append(form)
                continue
            slug = slugify(lemma)
            prefix = name.replace("_", "")  # dwugde, dwugen, durel, surel
            word_uri = WDR[f"word-{prefix}-{slug}"]
            s1 = WDR[f"sense-{prefix}-{slug}-t1"]
            s2 = WDR[f"sense-{prefix}-{slug}-t2"]

            g.add((word_uri, RDF.type, DRIFT.Word))
            g.add((word_uri, DRIFT.writtenForm, Literal(form, lang=lang)))
            g.add((word_uri, DRIFT.language, Literal(lang, datatype=XSD.language)))
            g.add((word_uri, RDFS.label, Literal(form, lang=lang)))
            g.add((word_uri, DRIFT.hasSource, src))

            for s_uri, plabel, pyear in (
                (s1, f"earlier period (~{earlier_y})", earlier_y),
                (s2, f"later period (~{later_y})", later_y),
            ):
                g.add((s_uri, RDF.type, DRIFT.Sense))
                g.add((s_uri, DRIFT.gloss, Literal(
                    f"Usage sense of '{form}' in the {plabel} of {meta['label']}", lang="en")))
                g.add((s_uri, DRIFT.connotation, DRIFT.Neutral))
                g.add((s_uri, DRIFT.firstAttested, Literal(f"{pyear:04d}", datatype=XSD.gYear)))
                g.add((s_uri, DRIFT.hasSource, src))
                g.add((word_uri, ONTOLEX.sense, s_uri))

            ev = WDR[f"drift-{prefix}-{slug}"]
            g.add((ev, RDF.type, DRIFT.DriftEvent))
            g.add((ev, DRIFT.affectsWord, word_uri))
            g.add((ev, DRIFT.senseFrom, s1))
            g.add((ev, DRIFT.senseTo, s2))
            # The benchmark gold records THAT a word changed + by how much, not the
            # direction. drift:Broadening is the conservative default the in-repo
            # SemEval adapter also uses (the DriftTypeScheme has no neutral umbrella
            # concept and this workstream must not change ontology semantics).
            g.add((ev, DRIFT.driftType, DRIFT.Broadening))
            g.add((ev, DRIFT.driftYear, Literal(f"{drift_y:04d}", datatype=XSD.gYear)))
            g.add((ev, DRIFT.gradedChange, Literal(graded, datatype=XSD.decimal)))
            g.add((ev, DRIFT.hasSource, src))

            ingested.append((form, lemma, binary, graded))
            have.add(form.lower())  # guard against intra-dataset dupes too

    return g, ingested, skipped, all_scores


# ---------------------------------------------------------------------------
# ChangeSignalAlignment lift
# ---------------------------------------------------------------------------

def build_alignment_graph(per_dataset: dict, curated_hyps: dict):
    """
    For every benchmark word (ingested OR deduped) that matches a curated word with
    a CausalHypothesis, add a ChangeSignalAlignment evidence stub on the existing
    wdr:hyp-* IRI. The gold graded-change score is the alignment evidence, so it
    applies even when the word's Word node already exists in examples/ (deduped).
    Returns (graph, alignments) where alignments = [(form, dataset, graded, [hyps])].
    """
    g = make_graph()
    alignments = []

    # collect first so we only emit the shared source/agent if there is >=1 alignment.
    # use all_scores (every row) so curated words deduped against examples/ still lift.
    pending = []
    for name, (meta, _ingested, _skipped, all_scores) in per_dataset.items():
        lang = meta["lang"]
        best = {}  # slug -> (form, graded) keep the highest graded if multiple rows
        for form, lemma, binary, graded in all_scores:
            key = (slugify(form), lang)
            if key in curated_hyps and (key not in best or graded > best[key][1]):
                best[key] = (form, graded)
        for key, (form, graded) in best.items():
            pending.append((form, name, meta, graded, curated_hyps[key]))

    if not pending:
        return g, alignments

    g.add((ALIGN_SOURCE_IRI, RDF.type, DRIFT.Corpus))
    g.add((ALIGN_SOURCE_IRI, DCT.title, Literal(
        "IMS Stuttgart WUG benchmarks -- gold graded-change signal (DWUG/DURel/SURel)",
        lang="en")))
    g.add((ALIGN_SOURCE_IRI, DRIFT.sourceURL, Literal(
        "https://www.ims.uni-stuttgart.de/en/research/resources/experiment-data/wugs/",
        datatype=XSD.anyURI)))
    g.add((ALIGN_SOURCE_IRI, RDFS.comment, Literal(
        "Per-word gold graded-change scores from the WUG benchmark datasets "
        "(data/wugs/*.ttl). The benchmark's own change measure is the field's "
        "accepted reproducible change signal; used here as ChangeSignalAlignment "
        "evidence for an existing curated hypothesis whose trigger date aligns "
        "with the measured shift. Cites the gold score, never asserts a cause.",
        lang="en")))
    g.add((ALIGN_AGENT_IRI, RDF.type, PROV.Agent))
    g.add((ALIGN_AGENT_IRI, RDFS.label, Literal(
        "WORD-DRIFT WUG ChangeSignalAlignment curator (full-benchmark ingest)", lang="en")))

    seen = set()
    for form, name, meta, graded, hyps in pending:
        for hyp_name in hyps:
            hyp = WDR[hyp_name]
            if hyp_name not in seen:
                g.add((hyp, DRIFT.evidenceType, DRIFT.ChangeSignalAlignment))
                g.add((hyp, DRIFT.hasSource, ALIGN_SOURCE_IRI))
                seen.add(hyp_name)
        alignments.append((form, meta["label"], graded, hyps))
    return g, alignments


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    ap = argparse.ArgumentParser(description="WUG benchmarks -> drift: ETL adapter")
    ap.add_argument("--report", action="store_true", help="print per-dataset summary")
    args = ap.parse_args()

    existing_forms, curated_hyps = _load_context()
    print(f"context: {sum(len(v) for v in existing_forms.values())} existing forms, "
          f"{len(curated_hyps)} curated words with a CausalHypothesis")

    per_dataset = {}
    total_new = 0
    new_de = 0
    for name, meta in DATASETS.items():
        csv_path = CACHE / meta["csv"]
        if not csv_path.exists():
            print(f"  SKIP {name}: groupings file not found ({csv_path}) -- run etl/scripts/fetch_wugs.sh")
            continue
        g, ingested, skipped, all_scores = build_dataset_graph(name, meta, existing_forms)
        out = OUT_DIR / f"{name}.ttl"
        write_turtle(g, out)
        conforms, report = validate_against_shapes(g)
        print(f"  {name}: {len(ingested)} new, {len(skipped)} deduped  "
              f"(SHACL conforms={conforms}, triples={len(g)})")
        if not conforms:
            print(report)
        per_dataset[name] = (meta, ingested, skipped, all_scores)
        total_new += len(ingested)
        if meta["lang"] == "de":
            new_de += len(ingested)

    align_g, alignments = build_alignment_graph(per_dataset, curated_hyps)
    if len(align_g):
        write_turtle(align_g, ALIGN_OUT)
        conforms, report = validate_against_shapes(align_g)
        print(f"  alignment: {len(alignments)} ChangeSignalAlignment evidence(s) "
              f"(SHACL conforms={conforms})")
    else:
        print("  alignment: no curated overlaps, nothing written")

    print(f"\nTOTAL new benchmark words: {total_new}  (German: {new_de})")

    if args.report:
        print("\n=== per-dataset detail ===")
        for name, (meta, ingested, skipped, _all) in per_dataset.items():
            print(f"\n{meta['label']} ({name}, {meta['lang']}): "
                  f"{len(ingested)} new / {len(skipped)} deduped")
            if skipped:
                print(f"  deduped: {sorted(skipped)}")
        print("\n=== ChangeSignalAlignment ===")
        for form, label, graded, hyps in alignments:
            print(f"  {form} ({label}, gradedChange={graded}) -> {hyps}")


if __name__ == "__main__":
    main()
