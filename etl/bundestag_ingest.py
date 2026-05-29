"""W12 — Bundestag plenary protocols → MeaningAttribution per Fraktion.

SKETCH (NOT a finished pipeline). Fetches a small sample of recent
Bundestag plenary protocols as XML, scans each speech (``<rede>``) for
mentions of a target word, and emits one
``drift:MeaningAttribution`` per (Fraktion, year) cell.

Per the workspace memory rule "Bundestag aggregates speaker to
Fraktion" we NEVER attribute to individual speakers. Each speech is
aggregated up to its Fraktion before any TTL is emitted.

Why this is a sketch
--------------------
1. We treat all mentions of the target word as evidence for ONE
   pre-declared sense (no in-protocol sense classification — a real
   pipeline would need an LLM step). The point is the Fraktion-as-
   Group mapping, not the sense classification.
2. We hit at most ``--n-protocols`` protocols and cap each at the
   first ~2 MB of XML so the script stays under a minute.
3. We do not store speaker IDs, speaker names, or speech text — only
   per-Fraktion counts.

Output: ``data/bundestag-sample.ttl``.
"""
from __future__ import annotations

import argparse
import logging
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("word_drift.etl.bundestag")

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_DATA_ROOT = _REPO_ROOT / "data"

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)

# Filterlist AJAX endpoint that drives the protocol archive page.
_FILTER_URL = (
    "https://www.bundestag.de/ajax/filterlist/de/dokumente/protokolle/"
    "plenarprotokolle/866354-866354"
)

_XML_RE = re.compile(r'https://www\.bundestag\.de/resource/blob/[^"]+\.xml')
_DATE_RE = re.compile(r'sitzung-datum="(\d{2})\.(\d{2})\.(\d{4})"')


# --- HTTP ------------------------------------------------------------------


def _get(url: str, *, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def _list_protocol_urls(n: int = 5, *, offset: int = 0) -> list[str]:
    url = f"{_FILTER_URL}?limit={n}&noFilterSet=true&offset={offset}"
    html = _get(url).decode("utf-8", errors="replace")
    urls = _XML_RE.findall(html)
    # de-dupe preserving order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out[:n]


# --- XML parse -------------------------------------------------------------


def _fraktion_for(rede: ET.Element) -> str | None:
    """Return the first Fraktion label found inside a <rede> element."""
    # Speakers appear as <redner><name>...<fraktion>...</fraktion></name></redner>
    for fr in rede.iter("fraktion"):
        text = (fr.text or "").strip()
        if text:
            return text
    return None


def _speech_text(rede: ET.Element) -> str:
    """Concatenate all text inside a <rede> element."""
    return "".join(rede.itertext())


# --- canonicalise Fraktion names ------------------------------------------

_FRAKTION_CANON = {
    "CDU/CSU": "cducsu",
    "CDU": "cducsu",
    "CSU": "cducsu",
    "SPD": "spd",
    "AfD": "afd",
    "FDP": "fdp",
    "DIE LINKE": "linke",
    "DIE LINKE.": "linke",
    "Die Linke": "linke",
    "BÜNDNIS 90/DIE GRÜNEN": "gruene",
    "Bündnis 90/Die Grünen": "gruene",
    "BSW": "bsw",
    "fraktionslos": "fraktionslos",
    "Fraktionslos": "fraktionslos",
}


def _canon_fraktion(s: str) -> str | None:
    s = s.strip()
    if not s:
        return None
    if s in _FRAKTION_CANON:
        return _FRAKTION_CANON[s]
    # try case-insensitive match
    for k, v in _FRAKTION_CANON.items():
        if k.lower() == s.lower():
            return v
    return None


# --- TTL -------------------------------------------------------------------


_PRELUDE = """@prefix drift:   <https://w3id.org/word-drift/ontology#> .
@prefix wdr:     <https://w3id.org/word-drift/resource/> .
@prefix ontolex: <http://www.w3.org/ns/lemon/ontolex#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix dct:     <http://purl.org/dc/terms/> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
"""


_FRAKTION_LABEL = {
    "cducsu": "CDU/CSU",
    "spd": "SPD",
    "afd": "AfD",
    "fdp": "FDP",
    "linke": "Die Linke",
    "gruene": "Bündnis 90/Die Grünen",
    "bsw": "BSW",
    "fraktionslos": "Fraktionslos",
}


def emit_ttl(
    *,
    word: str,
    sense_iri: str,
    counts: dict[tuple[str, int], int],
    protocols: list[dict[str, str]],
) -> str:
    lines = [_PRELUDE]
    lines.append(
        f"# Bundestag plenary sketch — word = {word}.\n"
        "# Each mention of the target word is aggregated to the speaker's\n"
        "# Fraktion (never the individual). No speech text or speaker IDs\n"
        "# are stored. See etl/bundestag_ingest.py for caveats.\n"
    )

    src_iri = f"wdr:src-bundestag-{word}-sample"
    lines.append(
        f"{src_iri} a drift:Source ;\n"
        f"    rdfs:label \"Bundestag plenary protocols (sample)\"@en ;\n"
        f"    drift:sourceURL \"https://www.bundestag.de/dokumente/protokolle/plenarprotokolle\"^^xsd:anyURI ;\n"
        f"    skos:note \"Sampled {len(protocols)} XML protocols; per-Fraktion aggregates only.\"@en .\n"
    )

    seen_fr = sorted({fr for fr, _ in counts.keys()})
    for fr in seen_fr:
        label = _FRAKTION_LABEL.get(fr, fr)
        gid = f"wdr:group-bundestag-{fr}"
        lines.append(
            f"{gid} a drift:Group ;\n"
            f"    rdfs:label \"Bundestagsfraktion {label}\"@de ;\n"
            f"    drift:groupKind drift:Political ;\n"
            f"    skos:note \"Aggregation of all speakers of this Fraktion across the sampled protocols.\"@en .\n"
        )

    for (fr, year), n in sorted(counts.items()):
        gid = f"wdr:group-bundestag-{fr}"
        attrib_iri = f"wdr:attrib-bundestag-{word}-{fr}-{year}"
        weight = round(min(1.0, n / 10.0), 4)
        lines.append(
            f"{attrib_iri} a drift:MeaningAttribution ;\n"
            f"    drift:attributesWord wdr:word-{word} ;\n"
            f"    drift:attributesSense {sense_iri} ;\n"
            f"    drift:byGroup {gid} ;\n"
            f"    drift:atYear \"{year}\"^^xsd:gYear ;\n"
            f"    drift:attributionWeight {weight:.4f} ;\n"
            f"    drift:hasEvidence {src_iri} ;\n"
            f"    skos:note \"{n} speeches in sampled protocol(s) mention this word\" .\n"
        )

    return "\n".join(lines)


# --- ingest ---------------------------------------------------------------


def ingest(
    *,
    word: str,
    sense_iri: str,
    out_path: Path,
    n_protocols: int = 5,
    offsets: tuple[int, ...] = (0, 100, 200),
) -> dict[str, Any]:
    # Gather candidate URLs from several archive pages so we get
    # multiple time slices.
    seen: set[str] = set()
    urls: list[str] = []
    for off in offsets:
        try:
            for u in _list_protocol_urls(n=n_protocols, offset=off):
                if u not in seen:
                    seen.add(u)
                    urls.append(u)
        except Exception as exc:  # noqa: BLE001
            logger.debug("offset %d listing failed: %s", off, exc)
            continue
        time.sleep(0.5)
        if len(urls) >= n_protocols * len(offsets):
            break

    urls = urls[:n_protocols]
    logger.info("Bundestag: sampling %d protocols", len(urls))

    counts: dict[tuple[str, int], int] = defaultdict(int)
    proto_info: list[dict[str, str]] = []
    word_re = re.compile(re.escape(word), re.IGNORECASE)

    for url in urls:
        try:
            blob = _get(url, timeout=60)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch failed %s: %s", url, exc)
            continue
        # Extract date from raw XML attribute (cheap pre-parse).
        m = _DATE_RE.search(blob.decode("utf-8", errors="replace"))
        if m:
            yyyy = int(m.group(3))
        else:
            yyyy = 0
        proto_info.append({"url": url, "year": str(yyyy)})

        try:
            root = ET.fromstring(blob)
        except ET.ParseError as exc:
            logger.warning("XML parse error %s: %s", url, exc)
            continue

        for rede in root.iter("rede"):
            fr_raw = _fraktion_for(rede)
            if not fr_raw:
                continue
            fr_canon = _canon_fraktion(fr_raw)
            if not fr_canon:
                continue
            text = _speech_text(rede)
            n_mentions = len(word_re.findall(text))
            if n_mentions == 0:
                continue
            counts[(fr_canon, yyyy)] += n_mentions
        time.sleep(0.5)

    ttl = emit_ttl(
        word=word,
        sense_iri=sense_iri,
        counts=counts,
        protocols=proto_info,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ttl, encoding="utf-8")
    return {
        "n_protocols": len(proto_info),
        "n_cells": len(counts),
        "total_mentions": sum(counts.values()),
        "out_path": str(out_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--word", default="Querdenker",
                        help="Word to count per Fraktion (default Querdenker)")
    parser.add_argument("--sense-iri", default="wdr:sense-querdenker-covid",
                        help="Sense IRI to attribute the mentions to")
    parser.add_argument("--n-protocols", type=int, default=5)
    parser.add_argument("--out", type=Path,
                        default=_DATA_ROOT / "bundestag-sample.ttl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    summary = ingest(
        word=args.word,
        sense_iri=args.sense_iri,
        out_path=args.out,
        n_protocols=args.n_protocols,
    )
    print(f"[bundestag] {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
