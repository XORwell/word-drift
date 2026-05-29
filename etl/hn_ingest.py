"""W12 — Hacker News sketch → MeaningAttribution.

SKETCH (NOT a finished pipeline). For ONE English word ("based"; the
2010s-incel-slang → 2020s-positive-reappropriation drift) we hit the
public HN Algolia search endpoint (https://hn.algolia.com/api), sample
about 50 stories+comments that contain the word, and bucket them by
TIME-WINDOW and by SENSE using a simple keyword heuristic.

Why this is a sketch
--------------------
1. The sense heuristic is *exact*: a co-occurring "based on" / "based in"
   / "is based" phrase is classified as the LITERAL "based" sense; if
   the word appears as a standalone token in a positive/agreement
   context (preceded by "absolutely", "totally", "you are", at start of
   a comment, etc.) we classify as the SLANG sense; anything else is
   AMBIGUOUS and is dropped. A real pipeline would use an LLM or a
   trained classifier.
2. We store ONLY counts and aggregated weights — never individual user
   handles, comment text, or story titles (per the workspace's PII
   memory entries).
3. The HN API returns at most 1000 hits per query; we cap at 100.

Output: ``data/hn-sample.ttl``.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("word_drift.etl.hn")

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_DATA_ROOT = _REPO_ROOT / "data"

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)


# --- sense classifier (heuristic) -----------------------------------------


# Literal "based": "based on/in", "X-based", "is based at"
_LITERAL_PATTERNS = [
    re.compile(r"\b[Bb]ased\s+(?:on|in|at|out\s+of|around|upon)\b"),
    re.compile(r"\b[Bb]ased[\s,]+(?:in|on)\s+(?:[A-Z]|the\s)"),
    re.compile(r"-based\b"),  # "Berlin-based", "open-source-based"
    re.compile(r"\b(?:is|are|was|were|were\s+all)\s+based\b"),
]

# Slang "based": standalone affirmation. We look for the word at
# sentence-initial position, or following typical agreement markers.
_SLANG_PATTERNS = [
    re.compile(r"^\s*[Bb]ased[.!?\s]*$"),  # entire comment = "Based."
    re.compile(r"\b(?:absolutely|totally|so|very|kinda|honestly)\s+based\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+are|that's|this\s+is|he\s+is|she\s+is)\s+based\b", re.IGNORECASE),
    re.compile(r"\bbased\s+and\s+(?:redpilled|red[\s-]?pilled)\b", re.IGNORECASE),
]


def classify_sense(text: str) -> str | None:
    """Return 'literal', 'slang', or None for ambiguous/no-match."""
    if not text:
        return None
    has_literal = any(p.search(text) for p in _LITERAL_PATTERNS)
    has_slang = any(p.search(text) for p in _SLANG_PATTERNS)
    if has_literal and not has_slang:
        return "literal"
    if has_slang and not has_literal:
        return "slang"
    # If both or neither, leave ambiguous so the corpus stays clean.
    return None


# --- fetch -----------------------------------------------------------------


def _algolia_search(query: str, *, tags: str, hits_per_page: int = 50,
                    page: int = 0, numeric_filters: str | None = None,
                    by_date: bool = False) -> dict[str, Any]:
    base = "https://hn.algolia.com/api/v1/" + ("search_by_date" if by_date else "search")
    params: dict[str, str] = {
        "query": query,
        "tags": tags,
        "hitsPerPage": str(hits_per_page),
        "page": str(page),
    }
    if numeric_filters:
        params["numericFilters"] = numeric_filters
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _fetch_hits(word: str, *, n: int = 100) -> list[dict[str, Any]]:
    """Return up to ``n`` HN hits (mix of stories + comments) for ``word``.

    To get TIME diversity we slice the query into year windows and pull
    a small batch per year. This is the only way to see drift over time
    on HN; the default ranking is purely relevance-based.
    """
    out: list[dict[str, Any]] = []
    # Slice into year windows. HN started Feb 2007; "based" slang took
    # off around 2018. Sample 5 years before and 5 years after.
    year_windows = [(2012, 2015), (2016, 2018), (2019, 2021), (2022, 2024), (2025, 2026)]
    hits_per_window = max(5, n // len(year_windows))
    for lo, hi in year_windows:
        lo_ts = int(time.mktime(time.strptime(f"{lo}-01-01", "%Y-%m-%d")))
        hi_ts = int(time.mktime(time.strptime(f"{hi}-12-31", "%Y-%m-%d")))
        nf = f"created_at_i>={lo_ts},created_at_i<={hi_ts}"
        for tag in ("comment",):
            try:
                data = _algolia_search(
                    word, tags=tag, hits_per_page=hits_per_window,
                    page=0, numeric_filters=nf, by_date=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("HN slice %d-%d failed: %s", lo, hi, exc)
                continue
            hits = data.get("hits", [])
            out.extend(hits)
            time.sleep(0.4)
            if len(out) >= n:
                break
        if len(out) >= n:
            break
    return out[:n]


# --- emit ------------------------------------------------------------------


_PRELUDE = """@prefix drift:   <https://w3id.org/word-drift/ontology#> .
@prefix wdr:     <https://w3id.org/word-drift/resource/> .
@prefix ontolex: <http://www.w3.org/ns/lemon/ontolex#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix dct:     <http://purl.org/dc/terms/> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
"""


def emit_ttl(
    *,
    word: str,
    counts: dict[tuple[str, int], int],
    word_iri: str | None = None,
) -> str:
    """Render the Source/Group/MeaningAttribution TTL block.

    ``counts`` keys are ``(sense, year)`` tuples; values are int counts.

    If ``word_iri`` is given, the MeaningAttribution records target that
    existing Word IRI and we do NOT mint a new Word entity. This avoids
    a writtenForm collision when an existing fixture (e.g. examples/
    based.ttl ↔ wdr:word-based) already declares the word.
    """
    lines = [_PRELUDE]
    lines.append(
        f"# Hacker News sketch — word = {word}.\n"
        "# Sense classification is heuristic (see etl/hn_ingest.py). Only\n"
        "# aggregated counts are stored; no user handles, story IDs, or\n"
        "# comment text.\n"
    )

    src_iri = f"wdr:src-hn-{word}-search"
    lines.append(
        f"{src_iri} a drift:Source ;\n"
        f"    rdfs:label \"Hacker News full-text search via Algolia — {word}\"@en ;\n"
        f"    drift:sourceURL \"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(word)}\"^^xsd:anyURI ;\n"
        f"    skos:note \"Aggregated counts only; no user handles or text spans stored.\"@en .\n"
    )

    # One Group per HN community as a whole. We do NOT subdivide by user.
    gid = f"wdr:group-hn-en"
    lines.append(
        f"{gid} a drift:Group ;\n"
        f"    rdfs:label \"Hacker News commenters (EN)\"@en ;\n"
        f"    drift:groupKind drift:PlatformNative ;\n"
        f"    drift:communityHandle \"news.ycombinator.com\" ;\n"
        f"    skos:note \"All comment/story authors on news.ycombinator.com, aggregated.\"@en .\n"
    )

    sense_iris = {
        "literal": f"wdr:sense-hn-{word}-literal",
        "slang":   f"wdr:sense-hn-{word}-slang",
    }
    for label, sense_iri in sense_iris.items():
        gloss = {
            "literal": f"literal sense of '{word}' (e.g. 'based in Berlin'); pre-slang reading",
            "slang":   f"approval / agreement slang reading of '{word}' (mid-2010s onward)",
        }[label]
        lines.append(
            f"{sense_iri} a drift:Sense ;\n"
            f"    drift:gloss \"{gloss}\"@en ;\n"
            f"    skos:notation \"hn-{word}-{label}\" .\n"
        )

    target_word_iri = word_iri or f"wdr:word-hn-{word}"

    # Attribution records per (sense, year)
    for (sense, year), n in sorted(counts.items()):
        if sense not in sense_iris:
            continue
        sense_iri = sense_iris[sense]
        attrib_iri = f"wdr:attrib-hn-{word}-{sense}-{year}"
        # Normalise count to a weight in [0,1] capped at 20.
        weight = round(min(1.0, n / 20.0), 4)
        lines.append(
            f"{attrib_iri} a drift:MeaningAttribution ;\n"
            f"    drift:attributesWord {target_word_iri} ;\n"
            f"    drift:attributesSense {sense_iri} ;\n"
            f"    drift:byGroup {gid} ;\n"
            f"    drift:atYear \"{year}\"^^xsd:gYear ;\n"
            f"    drift:attributionWeight {weight:.4f} ;\n"
            f"    drift:hasEvidence {src_iri} ;\n"
            f"    skos:note \"{n} HN posts matching heuristic\" .\n"
        )

    # Mint a local Word only if no external target was supplied. This
    # avoids writtenForm collisions with fixtures like examples/based.ttl
    # that already declare wdr:word-based.
    if not word_iri:
        lines.append(
            f"wdr:word-hn-{word} a drift:Word ;\n"
            f"    drift:writtenForm \"{word}\"@en ;\n"
            f"    drift:language \"en\" ;\n"
            f"    rdfs:label \"{word}\"@en ;\n"
            f"    ontolex:sense {sense_iris['literal']}, {sense_iris['slang']} .\n"
        )

    return "\n".join(lines)


def ingest(*, word: str, out_path: Path, n: int = 100,
           word_iri: str | None = None) -> dict[str, Any]:
    hits = _fetch_hits(word, n=n)
    logger.info("HN: fetched %d hits for %r", len(hits), word)

    counts: dict[tuple[str, int], int] = defaultdict(int)
    n_classified = 0
    n_ambiguous = 0
    for h in hits:
        text = h.get("comment_text") or h.get("story_text") or h.get("title") or ""
        sense = classify_sense(text)
        if sense is None:
            n_ambiguous += 1
            continue
        ts = h.get("created_at_i")
        if not ts:
            continue
        try:
            year = time.gmtime(int(ts)).tm_year
        except (TypeError, ValueError):
            continue
        counts[(sense, year)] += 1
        n_classified += 1

    ttl = emit_ttl(word=word, counts=counts, word_iri=word_iri)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ttl, encoding="utf-8")
    return {
        "n_hits": len(hits),
        "n_classified": n_classified,
        "n_ambiguous": n_ambiguous,
        "n_cells": len(counts),
        "out_path": str(out_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--word", default="based",
                        help="Word to query for (default: based)")
    parser.add_argument("--word-iri", default="wdr:word-based",
                        help="Pre-existing Word IRI to attach attributions to. "
                             "Pass empty string to mint a new wdr:word-hn-<word>.")
    parser.add_argument("--n", type=int, default=100,
                        help="Max HN hits to retrieve (default 100)")
    parser.add_argument("--out", type=Path,
                        default=_DATA_ROOT / "hn-sample.ttl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    summary = ingest(
        word=args.word,
        out_path=args.out,
        n=args.n,
        word_iri=args.word_iri or None,
    )
    print(f"[hn] {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
