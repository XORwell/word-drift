"""W12 — DWUG DE/EN → MeaningAttribution ingest.

Produces RDF Turtle for ``data/dwug-de.ttl`` and ``data/dwug-en.ttl`` from
the local DWUG caches under ``etl/.cache/dwug_de`` and ``etl/.cache/dwug_en``.

Data model
----------
For each lemma in the cache we read three CSV tables (tab-separated):

* ``data/<lemma>/uses.csv``      — one row per attested USAGE (with its
  ``grouping`` 1 or 2 — DWUG's coarse time bucket — and a ``date`` year).
* ``data/<lemma>/judgments.csv`` — pairwise graded similarity judgments
  on pairs of usages, scale 1 (unrelated) … 4 (identical), with 0
  reserved for "cannot decide". One row per (annotator, pair) judgment.
* ``clusters/opt/<lemma>.csv``   — the optimised cluster assignment per
  usage identifier (cluster -1 means "noise / unassigned").

The mapping to the drift vocabulary is:

* one ``drift:Sense`` per cluster (excluding -1 noise) with a
  deterministic IRI ``wdr:sense-dwug-<lang>-<lemma>-c<N>``;
* one ``drift:Group`` per DWUG ``annotator`` handle, with a
  deterministic IRI ``wdr:group-dwug-<lang>-<annotator>``;
* one ``drift:MeaningAttribution`` per (lemma, sense, annotator,
  grouping) triple where the annotator gave at least one judgment on a
  pair of usages BOTH belonging to that cluster. The
  ``drift:attributionWeight`` is the rater's average normalised
  agreement on those in-cluster pairs:

      weight = mean( (judgment - 1) / 3 ) for judgments in {1,2,3,4}

  i.e. a judgment of 4 ("identical") contributes weight 1.0, a 1
  ("unrelated") contributes 0.0, and "cannot decide" (0) is dropped.

The ``drift:atYear`` slot uses the median date of the in-cluster usages
that fell into the same DWUG ``grouping`` bucket — this lets the
multi-group metrics line each attribution up on the same temporal axis
as the curated fixtures.

Word selection
--------------
We rank lemmas by the number of distinct annotators who covered them
and emit the top N (default 8 for DE, 8 for EN). The word-list is
logged at the end of the run.

The output is deterministic given the same input CSVs.
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("word_drift.etl.dwug")

# Repository roots ---------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_CACHE_ROOT = _THIS_FILE.parent / ".cache"
_DATA_ROOT = _REPO_ROOT / "data"

# Namespaces (kept in sync with ontology/) --------------------------------

WDR = "https://w3id.org/word-drift/resource/"
DRIFT = "https://w3id.org/word-drift/ontology#"


# --- helpers --------------------------------------------------------------


_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")


def _slug(s: str) -> str:
    """Lower-case, ASCII-safe slug for IRI suffixes."""
    # DWUG lemmas can contain umlauts and ß; normalise.
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae",
                            "Ö": "Oe", "Ü": "Ue", "ß": "ss"})
    return _SLUG_RE.sub("-", s.translate(table)).strip("-").lower()


def _read_tsv(path: Path) -> list[dict[str, str]]:
    """Read a DWUG tab-separated table into a list of row dicts."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def _lemma_dirs(cache_root: Path) -> list[Path]:
    data_dir = cache_root / "data"
    if not data_dir.exists():
        return []
    return sorted(p for p in data_dir.iterdir() if p.is_dir())


def _lemma_display(lemma: str) -> str:
    """DWUG-EN lemmas look like ``afternoon_nn``; strip the POS suffix."""
    if "_" in lemma and lemma.rsplit("_", 1)[-1] in {"nn", "vb", "jj", "rb"}:
        return lemma.rsplit("_", 1)[0]
    return lemma


# --- core ingest ----------------------------------------------------------


def _rank_lemmas_by_annotator_coverage(cache_root: Path) -> list[tuple[str, int]]:
    """Rank lemmas by the count of distinct annotators on their judgments."""
    ranked: list[tuple[str, int]] = []
    for d in _lemma_dirs(cache_root):
        judg = d / "judgments.csv"
        if not judg.exists():
            continue
        annotators: set[str] = set()
        for row in _read_tsv(judg):
            annotators.add(row.get("annotator", "").strip())
        annotators.discard("")
        ranked.append((d.name, len(annotators)))
    ranked.sort(key=lambda t: (-t[1], t[0]))
    return ranked


def _attribution_records_for_lemma(
    cache_root: Path,
    lemma: str,
) -> Iterator[dict]:
    """Yield one record per (cluster, annotator, grouping) triple."""
    lemma_dir = cache_root / "data" / lemma
    cluster_csv = cache_root / "clusters" / "opt" / f"{lemma}.csv"
    if not (lemma_dir / "judgments.csv").exists() or not cluster_csv.exists():
        return

    uses = _read_tsv(lemma_dir / "uses.csv")
    judgments = _read_tsv(lemma_dir / "judgments.csv")
    clusters_raw = _read_tsv(cluster_csv)

    # identifier -> cluster id (skip noise = -1)
    use_to_cluster: dict[str, int] = {}
    for r in clusters_raw:
        ident = r.get("identifier", "").strip()
        c_raw = r.get("cluster", "").strip()
        if not ident or not c_raw:
            continue
        try:
            c = int(c_raw)
        except ValueError:
            continue
        if c < 0:
            continue
        use_to_cluster[ident] = c

    # identifier -> (year:int|None, grouping:int|None)
    use_meta: dict[str, tuple[int | None, int | None]] = {}
    for r in uses:
        ident = r.get("identifier", "").strip()
        if not ident:
            continue
        year_s = r.get("date", "").strip()
        grp_s = r.get("grouping", "").strip()
        year: int | None = None
        if year_s:
            try:
                year = int(year_s[:4])
            except ValueError:
                year = None
        grp: int | None = None
        if grp_s:
            try:
                grp = int(grp_s)
            except ValueError:
                grp = None
        use_meta[ident] = (year, grp)

    # collect in-cluster pair judgments per (annotator, cluster, grouping)
    weights: dict[tuple[str, int, int], list[float]] = defaultdict(list)
    years: dict[tuple[str, int, int], list[int]] = defaultdict(list)

    for r in judgments:
        a = r.get("annotator", "").strip()
        i1 = r.get("identifier1", "").strip()
        i2 = r.get("identifier2", "").strip()
        j_s = r.get("judgment", "").strip()
        if not (a and i1 and i2 and j_s):
            continue
        try:
            j = int(j_s)
        except ValueError:
            continue
        if j < 1 or j > 4:
            continue
        c1 = use_to_cluster.get(i1)
        c2 = use_to_cluster.get(i2)
        if c1 is None or c2 is None or c1 != c2:
            continue
        cluster = c1
        # pick a grouping bucket. If both uses share grouping, use that.
        # Otherwise prefer the earlier (grouping=1).
        g1 = use_meta.get(i1, (None, None))[1]
        g2 = use_meta.get(i2, (None, None))[1]
        if g1 is None and g2 is None:
            continue
        grouping = g1 if g1 == g2 else (g1 or g2)
        if grouping is None:
            continue
        normalised = (j - 1) / 3.0  # 1 -> 0.0, 4 -> 1.0
        key = (a, cluster, grouping)
        weights[key].append(normalised)
        # collect years from both endpoints if available
        for uid in (i1, i2):
            y = use_meta.get(uid, (None, None))[0]
            if y is not None:
                years[key].append(y)

    for (annotator, cluster, grouping), w_list in sorted(weights.items()):
        if not w_list:
            continue
        weight = round(sum(w_list) / len(w_list), 4)
        # representative year = median of associated years (or None)
        y_list = years[(annotator, cluster, grouping)]
        rep_year: int | None = None
        if y_list:
            rep_year = int(statistics.median(y_list))
        yield {
            "annotator": annotator,
            "cluster": cluster,
            "grouping": grouping,
            "weight": weight,
            "n_pairs": len(w_list),
            "year": rep_year,
        }


# --- serialisation --------------------------------------------------------


_PRELUDE = """@prefix drift:   <https://w3id.org/word-drift/ontology#> .
@prefix wdr:     <https://w3id.org/word-drift/resource/> .
@prefix ontolex: <http://www.w3.org/ns/lemon/ontolex#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix dct:     <http://purl.org/dc/terms/> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
"""


def _format_groups_block(*, lang: str, annotators: list[str]) -> str:
    """Render the file-wide annotator Group declarations (emitted once)."""
    out: list[str] = []
    for a in sorted(annotators):
        gid = f"wdr:group-dwug-{lang}-{_slug(a)}"
        out.append(f"{gid} a drift:Group ;")
        out.append(f"    rdfs:label \"DWUG {lang.upper()} {a}\"@en ;")
        out.append(f"    drift:groupKind drift:Professional ;")
        out.append(
            f"    skos:note \"Pseudonymous DWUG-{lang.upper()} annotator handle; "
            f"used here as a Group proxy for inter-rater attribution weighting.\"@en .")
        out.append("")
    return "\n".join(out)


def _format_lemma_block(
    *,
    lemma: str,
    lang: str,
    display: str,
    records: list[dict],
    source_iri: str,
) -> str:
    """Render one lemma's Word/Sense/MeaningAttribution block.

    Annotator Groups are emitted once per file by
    :func:`_format_groups_block`, not here.
    """
    word_iri = f"wdr:word-dwug-{lang}-{_slug(lemma)}"
    out: list[str] = []
    out.append(f"# --- {display} ({lang}) ---------------------------------")
    out.append(f"{word_iri} a drift:Word ;")
    out.append(f"    drift:writtenForm \"{display}\"@{lang} ;")
    out.append(f"    drift:language \"{lang}\" ;")

    # collect unique clusters from records
    clusters = sorted({r["cluster"] for r in records})
    sense_iris = [f"wdr:sense-dwug-{lang}-{_slug(lemma)}-c{c}" for c in clusters]
    if sense_iris:
        out.append("    ontolex:sense " + ", ".join(sense_iris) + " ;")
    out.append(f"    rdfs:label \"{display}\"@{lang} .")
    out.append("")

    # sense declarations
    for c, sense_iri in zip(clusters, sense_iris):
        out.append(f"{sense_iri} a drift:Sense ;")
        out.append(
            f"    drift:gloss \"DWUG cluster {c} for {display} ({lang}); "
            f"definition derived from the cluster's usage cohort.\"@en ;"
        )
        out.append(f"    skos:notation \"dwug-{lang}-{_slug(lemma)}-c{c}\" .")
        out.append("")

    # attribution records, sorted for determinism
    for rec in sorted(records, key=lambda r: (r["annotator"], r["cluster"], r["grouping"])):
        gid = f"wdr:group-dwug-{lang}-{_slug(rec['annotator'])}"
        sense_iri = f"wdr:sense-dwug-{lang}-{_slug(lemma)}-c{rec['cluster']}"
        attrib_iri = (
            f"wdr:attrib-dwug-{lang}-{_slug(lemma)}"
            f"-{_slug(rec['annotator'])}-c{rec['cluster']}-g{rec['grouping']}"
        )
        out.append(f"{attrib_iri} a drift:MeaningAttribution ;")
        out.append(f"    drift:attributesWord {word_iri} ;")
        out.append(f"    drift:attributesSense {sense_iri} ;")
        out.append(f"    drift:byGroup {gid} ;")
        if rec["year"] is not None:
            out.append(f"    drift:atYear \"{rec['year']}\"^^xsd:gYear ;")
        out.append(f"    drift:attributionWeight {rec['weight']:.4f} ;")
        out.append(f"    prov:wasDerivedFrom <{source_iri}> ;")
        out.append(f"    skos:note \"derived from {rec['n_pairs']} in-cluster pair judgment(s)\" .")
        out.append("")

    return "\n".join(out)


def ingest(
    *,
    lang: str,
    cache_subdir: str,
    out_path: Path,
    n_words: int = 8,
) -> dict:
    """Ingest DWUG <lang> from cache, write TTL, return summary stats."""
    cache_root = _CACHE_ROOT / cache_subdir / cache_subdir
    if not cache_root.exists():
        # some caches double-nest (e.g. dwug_de/dwug_de/), some don't.
        cache_root = _CACHE_ROOT / cache_subdir
    if not cache_root.exists():
        raise FileNotFoundError(f"DWUG cache not found: {cache_root}")

    ranked = _rank_lemmas_by_annotator_coverage(cache_root)
    chosen = [lemma for lemma, _ in ranked[:n_words]]
    logger.info("DWUG %s: ranked %d lemmas, selecting top %d: %s",
                lang, len(ranked), len(chosen), chosen)

    source_iri = (
        "https://www2.ims.uni-stuttgart.de/data/wugs/"
        f"dwug_{lang}_v2.4.0/"
    )

    parts: list[str] = [_PRELUDE]
    parts.append(
        "# =============================================================\n"
        f"# DWUG {lang.upper()} → drift:MeaningAttribution (W12 ingest)\n"
        f"# Generated by etl/dwug_ingest.py. Input: etl/.cache/{cache_subdir}/.\n"
        f"# Words: {', '.join(_lemma_display(l) for l in chosen)}.\n"
        "# Each cluster in the DWUG usage graph becomes a drift:Sense; each\n"
        "# DWUG annotator becomes a drift:Group; each in-cluster pair\n"
        "# judgment contributes to that (annotator, cluster, grouping)'s\n"
        "# drift:attributionWeight via (judgment-1)/3.\n"
        "# =============================================================\n"
    )

    # Provenance node for the corpus.
    src_node = f"wdr:src-dwug-{lang}"
    parts.append(
        f"<{source_iri}> a prov:Entity ;\n"
        f"    rdfs:label \"DWUG {lang.upper()} v2.4.0 (Schlechtweg et al.)\"@en ;\n"
        f"    dct:source \"https://www2.ims.uni-stuttgart.de/data/wugs/\" .\n"
    )

    total_attribs = 0
    word_summaries: list[dict] = []
    lemma_records: dict[str, list[dict]] = {}
    all_annotators: set[str] = set()
    for lemma in chosen:
        records = list(_attribution_records_for_lemma(cache_root, lemma))
        if not records:
            logger.warning("DWUG %s/%s: no in-cluster pair judgments — skipping",
                           lang, lemma)
            continue
        lemma_records[lemma] = records
        all_annotators.update(r["annotator"] for r in records)

    if all_annotators:
        parts.append(_format_groups_block(
            lang=lang, annotators=sorted(all_annotators),
        ))

    for lemma in chosen:
        records = lemma_records.get(lemma)
        if not records:
            continue
        block = _format_lemma_block(
            lemma=lemma,
            lang=lang,
            display=_lemma_display(lemma),
            records=records,
            source_iri=source_iri,
        )
        parts.append(block)
        total_attribs += len(records)
        word_summaries.append({
            "lemma": lemma,
            "display": _lemma_display(lemma),
            "n_attributions": len(records),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return {
        "lang": lang,
        "out_path": str(out_path),
        "n_words": len(word_summaries),
        "n_attributions": total_attribs,
        "words": word_summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=["de", "en", "all"], default="all")
    parser.add_argument("--n-words", type=int, default=8,
                        help="Number of lemmas to ingest per language (default 8)")
    parser.add_argument("--data-dir", type=Path, default=_DATA_ROOT,
                        help="Output directory (default: word-drift/data/)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    targets: list[tuple[str, str, Path]] = []
    if args.lang in ("de", "all"):
        targets.append(("de", "dwug_de", args.data_dir / "dwug-de.ttl"))
    if args.lang in ("en", "all"):
        targets.append(("en", "dwug_en", args.data_dir / "dwug-en.ttl"))

    summaries = []
    for lang, sub, path in targets:
        try:
            s = ingest(lang=lang, cache_subdir=sub, out_path=path, n_words=args.n_words)
            summaries.append(s)
            print(f"[dwug] {lang}: {s['n_attributions']} MeaningAttributions, "
                  f"{s['n_words']} words → {s['out_path']}")
            for w in s["words"]:
                print(f"  - {w['display']:24s}  ({w['n_attributions']} attribs)")
        except FileNotFoundError as exc:
            logger.error("skipping %s: %s", lang, exc)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
