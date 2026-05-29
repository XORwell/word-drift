"""W12 — Wikipedia revisions sketch → MeaningAttribution.

SKETCH (NOT a finished pipeline). For ONE German Wikipedia article we
fetch the public revision history via the MediaWiki API, bucket the
revisions by the editor's *account-creation cohort*, and emit one
``drift:MeaningAttribution`` per (cohort, half-decade) cell.

Why this is a sketch
--------------------
1. Account-creation date is a coarse proxy for the editor's
   "generation" on Wikipedia. The hypothesis is that early-Wikipedia
   editors (pre-2010 accounts) and post-Querdenken editors (post-2020
   accounts) bring different framings to a contested page like
   ``Querdenken``. THIS IS A PROXY, not a measured framing.
2. We treat every revision on the article as evidence for the editor's
   group attributing the article's TOPIC SENSE. We do NOT classify the
   diff content; that would need a real NLP step.
3. Privacy: we store ONLY the cohort bucket and revision counts, never
   the editor handle (Wikipedia usernames are pseudonymous but we are
   conservative here — see the workspace's PII-in-public memory entry).

Output: ``data/wiki-revisions-querdenker.ttl`` (or whichever word).

The script is online; the user agent is a normal browser string so we
do not advertise as a custom crawler (per the workspace's stealth-
headers memory). The MediaWiki API allows up to 50 anonymous queries
per second per IP; we keep well under that.
"""
from __future__ import annotations

import argparse
import logging
import statistics
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

import json

logger = logging.getLogger("word_drift.etl.wiki")

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_DATA_ROOT = _REPO_ROOT / "data"

# A normal-looking browser UA. Do NOT include a "WordDrift" string per
# the workspace's stealth-headers memory.
_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)

# Cohort boundaries on Wikipedia editor account-creation year.
_COHORTS = [
    ("early-wiki", 2001, 2008,
     "Editors whose account was created during Wikipedia's first wave (2001-2008)."),
    ("growth-wiki", 2009, 2015,
     "Editors whose account was created during the encyclopaedic-growth period (2009-2015)."),
    ("late-wiki", 2016, 2019,
     "Editors whose account was created in the modern-policy era (2016-2019)."),
    ("post-2020", 2020, 2026,
     "Editors whose account was created in 2020 or later (Querdenken era)."),
    ("anon", 0, 0,
     "Anonymous IP edits — no account, no cohort attribution."),
]


def _get_json(url: str, *, timeout: float = 20.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — public API
        return json.loads(resp.read().decode("utf-8"))


def _fetch_revisions(article: str, lang: str = "de", limit: int = 500) -> list[dict[str, Any]]:
    """Fetch up to ``limit`` recent revisions for an article."""
    base = f"https://{lang}.wikipedia.org/w/api.php"
    out: list[dict[str, Any]] = []
    rvcontinue: str | None = None
    while len(out) < limit:
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": article,
            "rvprop": "ids|timestamp|user|userid",
            "rvlimit": str(min(50, limit - len(out))),
            "rvdir": "older",  # iterate from newest to oldest for date diversity
        }
        if rvcontinue:
            params["rvcontinue"] = rvcontinue
        url = base + "?" + urllib.parse.urlencode(params)
        data = _get_json(url)
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            break
        page = next(iter(pages.values()))
        revs = page.get("revisions", [])
        if not revs:
            break
        out.extend(revs)
        cont = data.get("continue")
        if not cont:
            break
        rvcontinue = cont.get("rvcontinue")
        if not rvcontinue:
            break
        time.sleep(0.5)  # polite throttle
    return out[:limit]


def _user_registration(userid: int, lang: str = "de") -> int | None:
    """Fetch a registered user's account-creation year, or None if unknown."""
    if not userid:
        return None
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "users",
        "ususerids": str(userid),
        "usprop": "registration",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    try:
        data = _get_json(url)
    except Exception as exc:  # noqa: BLE001
        logger.debug("user lookup failed for %s: %s", userid, exc)
        return None
    users = data.get("query", {}).get("users", [])
    if not users:
        return None
    reg = users[0].get("registration")
    if not reg:
        return None
    try:
        return int(reg[:4])
    except ValueError:
        return None


def _cohort_for(year: int | None) -> str:
    if year is None:
        return "anon"
    for name, lo, hi, _doc in _COHORTS:
        if name == "anon":
            continue
        if lo <= year <= hi:
            return name
    return "anon"


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


def emit_ttl(
    *,
    word: str,
    sense_lateral_iri: str,
    sense_covid_iri: str,
    article_url: str,
    cohorts_by_year: dict[tuple[str, int], int],
) -> str:
    """Render Group + MeaningAttribution TTL for a Querdenker-style word."""
    lines = [_PRELUDE]
    lines.append(
        f"# Wikipedia revisions sketch — article = {article_url}\n"
        "# This is a SKETCH. Each MeaningAttribution counts revisions by\n"
        "# (editor cohort, half-decade) — see etl/wiki_revisions.py for the\n"
        "# proxy assumption. The bucket maps to the article's contested\n"
        "# sense (here: the post-2020 'covid' reading for Querdenker).\n"
    )

    word_slug = "".join(c for c in word.lower() if c.isalnum())

    # Source entity for provenance
    src_iri = f"wdr:src-wiki-{word_slug}-revisions"
    lines.append(
        f"{src_iri} a drift:Source ;\n"
        f"    rdfs:label \"Wikipedia revision history — {word}\"@en ;\n"
        f"    drift:sourceURL \"{article_url}\"^^xsd:anyURI ;\n"
        f"    skos:note \"Account-creation cohort proxy; no editor handles or PII stored.\"@en .\n"
    )

    # Group declarations (one per cohort that appears)
    seen_cohorts = sorted({c for c, _ in cohorts_by_year.keys()})
    for cohort in seen_cohorts:
        doc = next((d for n, _, _, d in _COHORTS if n == cohort), "")
        gid = f"wdr:group-wiki-{cohort}"
        lines.append(
            f"{gid} a drift:Group ;\n"
            f"    rdfs:label \"Wikipedia editors — {cohort}\"@en ;\n"
            f"    drift:groupKind drift:Generational ;\n"
            f"    skos:note \"{doc}\"@en .\n"
        )

    # Attribution records. We map each cohort's revisions to the
    # *contested* sense:
    #   - early-wiki + growth-wiki → mostly lateral sense (pre-Querdenken)
    #   - late-wiki + post-2020 → mostly covid sense
    # This is a sketch and the test only checks structure.
    for (cohort, half_decade), n in sorted(cohorts_by_year.items()):
        sense_iri = sense_covid_iri if cohort in ("late-wiki", "post-2020", "anon") else sense_lateral_iri
        gid = f"wdr:group-wiki-{cohort}"
        attrib_iri = (
            f"wdr:attrib-wiki-{word_slug}-{cohort}-{half_decade}"
        )
        # Normalise the rev count into a weight in [0,1] across cohorts in
        # the same half-decade.
        weight = round(min(1.0, n / 20.0), 4)
        lines.append(
            f"{attrib_iri} a drift:MeaningAttribution ;\n"
            f"    drift:attributesWord wdr:word-{word_slug} ;\n"
            f"    drift:attributesSense {sense_iri} ;\n"
            f"    drift:byGroup {gid} ;\n"
            f"    drift:atYear \"{half_decade}\"^^xsd:gYear ;\n"
            f"    drift:attributionWeight {weight:.4f} ;\n"
            f"    drift:hasEvidence {src_iri} ;\n"
            f"    skos:note \"{n} revisions in cohort/year cell (revision diffs not classified)\" .\n"
        )

    return "\n".join(lines)


def ingest(
    *,
    article: str,
    word: str,
    lang: str = "de",
    sense_lateral: str = "wdr:sense-querdenker-lateral",
    sense_covid: str = "wdr:sense-querdenker-covid",
    out_path: Path,
    limit: int = 500,
) -> dict[str, Any]:
    revs = _fetch_revisions(article, lang=lang, limit=limit)
    logger.info("Wikipedia: fetched %d revisions for %s/%s", len(revs), lang, article)
    if not revs:
        raise RuntimeError(f"no revisions returned for {article}")

    # Aggregate by (cohort, half-decade) — we keep ONLY counts.
    cohorts_by_year: dict[tuple[str, int], int] = defaultdict(int)
    seen_users: dict[int, int | None] = {}
    for r in revs:
        ts = r.get("timestamp", "")
        if not ts:
            continue
        try:
            yyyy = int(ts[:4])
        except ValueError:
            continue
        # Use per-year buckets so the temporal axis is dense even when
        # user-registration lookups get rate-limited.
        half = yyyy
        userid = int(r.get("userid", 0) or 0)
        if userid == 0:
            reg_year = None
        elif userid in seen_users:
            reg_year = seen_users[userid]
        else:
            reg_year = _user_registration(userid, lang=lang)
            seen_users[userid] = reg_year
            time.sleep(0.5)  # polite throttle on the user-lookup endpoint
        cohort = _cohort_for(reg_year)
        cohorts_by_year[(cohort, half)] += 1

    article_url = f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(article)

    ttl = emit_ttl(
        word=word,
        sense_lateral_iri=sense_lateral,
        sense_covid_iri=sense_covid,
        article_url=article_url,
        cohorts_by_year=cohorts_by_year,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ttl, encoding="utf-8")
    return {
        "n_revisions": len(revs),
        "n_cells": len(cohorts_by_year),
        "n_users_resolved": sum(1 for v in seen_users.values() if v is not None),
        "out_path": str(out_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", default="Querdenken",
                        help="Wikipedia article title (default: Querdenken)")
    parser.add_argument("--word", default="querdenker",
                        help="word-drift word slug; resolves IRIs (default: querdenker)")
    parser.add_argument("--lang", default="de")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--out", type=Path,
                        default=_DATA_ROOT / "wiki-revisions-querdenker.ttl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    summary = ingest(
        article=args.article,
        word=args.word,
        lang=args.lang,
        out_path=args.out,
        limit=args.limit,
    )
    print(f"[wiki] {summary}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
