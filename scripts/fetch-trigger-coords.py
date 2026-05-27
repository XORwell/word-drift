#!/usr/bin/env python3
"""
fetch-trigger-coords.py -- geocode Wikidata-linked drift:TriggerEvent nodes.

Goal: produce geographic coordinates for trigger events that carry an
owl:sameAs link to a Wikidata Q-item, to power a future map view in the
explorer. Output is site/trigger-coords.json.

What it does
------------
1. Loads examples/ + data/ into one rdflib graph and finds every
   drift:TriggerEvent that has an owl:sameAs to a Wikidata Q-item, collecting
   {triggerId, label, QID, eventDate, category}.
2. For each QID, fetches the entity from Wikidata (wbgetentities action API)
   and reads a coordinate location:
     - P625 (coordinate location) -> coordSource "P625" (direct).
   If the entity itself has no P625 (typical for persons / works / orgs), it
   MAY fall back to a single, unambiguous related place and use THAT place's
   P625:
     - P19  (place of birth)        -> coordSource "P19" (person fallback)
     - P159 (headquarters location) -> coordSource "P159" (org fallback)
     - P740 (location of formation) -> coordSource "P740" (org/movement)
   The fallback is only taken when the property has exactly one value (no
   ambiguity); otherwise the trigger is left without coordinates. Persons /
   works with neither P625 nor an unambiguous place are expected and fine.
3. Emits site/trigger-coords.json: an array of objects
   {triggerId, label, qid, lat, lon, eventDate, category, coordSource} for
   ONLY the triggers with a defensible coordinate, plus top-level metadata
   (counts, source breakdown).

Re-runnable & polite
--------------------
* All HTTP responses cached under .cache/wikidata/ (keyed by request hash),
  the same scheme as resolve-trigger-qids.py; re-runs make zero network calls
  for already-seen lookups. The existing wbgetentities cache is reused.
* Small delay between *uncached* requests; descriptive User-Agent.

Cost: $0 (Wikidata is free, no LLM).

Usage
-----
    python scripts/fetch-trigger-coords.py            # geocode + write JSON
    python scripts/fetch-trigger-coords.py --dry-run  # geocode + print, no write
    python scripts/fetch-trigger-coords.py --limit 20 # only first N (debug)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

warnings.simplefilter("ignore")

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache" / "wikidata"
OUT_JSON = ROOT / "site" / "trigger-coords.json"

DRIFT = "https://w3id.org/word-drift/ontology#"
OWL = "http://www.w3.org/2002/07/owl#"
WD_ENTITY = "http://www.wikidata.org/entity/"

USER_AGENT = "word-drift-research/0.4 (https://w3id.org/word-drift; research@nennemann.de)"
REQUEST_DELAY_S = 0.6  # polite gap between *uncached* network requests

# Property used for a direct coordinate on the entity itself.
P_COORD = "P625"  # coordinate location

# Place-valued properties we may follow ONE hop to a coordinate, when the
# entity itself has no P625. Ordered by preference; the FIRST property that has
# exactly one place value (and that place resolves to a P625) wins. Each entry
# is (property, human-readable coordSource note).
PLACE_FALLBACK_PROPS = (
    "P19",   # place of birth (persons)
    "P159",  # headquarters location (organisations)
    "P740",  # location of formation (organisations / movements)
)


# --------------------------------------------------------------------------- #
# HTTP with on-disk cache (same scheme as resolve-trigger-qids.py)
# --------------------------------------------------------------------------- #
def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def http_get_json(url: str) -> dict:
    """GET a URL returning JSON, cached on disk. Polite delay on cache miss."""
    cp = _cache_path(url)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(REQUEST_DELAY_S)
    return data


def get_entity(qid: str) -> dict:
    """Fetch the full claims of a Wikidata entity (cached). Returns {} on error."""
    url = (
        "https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&format=json&ids={qid}&props=claims&languages=en"
    )
    try:
        data = http_get_json(url)
    except Exception:
        return {}
    return data.get("entities", {}).get(qid, {})


# --------------------------------------------------------------------------- #
# claim extraction
# --------------------------------------------------------------------------- #
def _coord_from_claims(claims: dict) -> tuple[float, float] | None:
    """Return (lat, lon) from a P625 globe-coordinate claim, or None.

    Prefers a 'preferred'-rank statement, then any 'normal'-rank one. Only
    accepts Earth globe coordinates (skip Moon/Mars/etc.).
    """
    stmts = claims.get(P_COORD, [])
    # rank preference: preferred > normal > deprecated
    rank_order = {"preferred": 0, "normal": 1, "deprecated": 2}
    for st in sorted(stmts, key=lambda s: rank_order.get(s.get("rank"), 1)):
        snak = st.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        dv = snak.get("datavalue", {}).get("value", {})
        if not isinstance(dv, dict):
            continue
        lat, lon = dv.get("latitude"), dv.get("longitude")
        globe = dv.get("globe", "")
        # default Wikidata globe (Earth) is Q2; reject other celestial bodies
        if globe and not globe.endswith("Q2"):
            continue
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            continue
        # Reject Null-Island-style placeholder coordinates: a longitude of
        # exactly 0 paired with an integer-degree latitude is, on Wikidata, a
        # data-entry placeholder rather than a real location (e.g. the German
        # reunification item carries lat 69 / lon 0). Not defensible as a map
        # point, so skip it. Genuine 0-meridian places have fractional values.
        if lon == 0 and float(lat).is_integer():
            continue
        return float(lat), float(lon)
    return None


def _single_place_value(claims: dict, prop: str) -> str | None:
    """Return the single QID value of `prop`, or None if absent / ambiguous.

    'Ambiguous' = the property has more than one distinct item value (we refuse
    to pick one arbitrarily). Prefers a single 'preferred'-rank value if present.
    """
    stmts = claims.get(prop, [])
    preferred: list[str] = []
    normal: list[str] = []
    for st in stmts:
        snak = st.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        dv = snak.get("datavalue", {}).get("value", {})
        if not isinstance(dv, dict) or "id" not in dv:
            continue
        qid = dv["id"]
        if st.get("rank") == "preferred":
            preferred.append(qid)
        elif st.get("rank") != "deprecated":
            normal.append(qid)
    # If exactly one preferred value, use it (disambiguates multi-value props).
    if len(set(preferred)) == 1:
        return preferred[0]
    if preferred:
        return None  # multiple preferred -> ambiguous
    if len(set(normal)) == 1:
        return normal[0]
    return None  # zero or multiple -> no unambiguous place


def coord_for_qid(qid: str) -> tuple[float, float, str] | None:
    """Resolve a coordinate for a QID. Returns (lat, lon, coordSource) or None.

    1. Direct P625 on the entity.
    2. Else, the first place-valued fallback property with a SINGLE value whose
       referenced place has a P625.
    """
    ent = get_entity(qid)
    if not ent:
        return None
    claims = ent.get("claims", {})

    direct = _coord_from_claims(claims)
    if direct is not None:
        return direct[0], direct[1], "P625"

    for prop in PLACE_FALLBACK_PROPS:
        place_qid = _single_place_value(claims, prop)
        if not place_qid:
            continue
        place_ent = get_entity(place_qid)
        if not place_ent:
            continue
        pcoord = _coord_from_claims(place_ent.get("claims", {}))
        if pcoord is not None:
            return pcoord[0], pcoord[1], prop
    return None


# --------------------------------------------------------------------------- #
# graph loading
# --------------------------------------------------------------------------- #
def load_qid_triggers() -> list[dict]:
    """All drift:TriggerEvent with an owl:sameAs to a Wikidata Q-item."""
    import rdflib

    g = rdflib.Graph()
    for pat in ["examples/**/*.ttl", "data/**/*.ttl"]:
        for f in glob.glob(str(ROOT / pat), recursive=True):
            try:
                g.parse(f, format="turtle")
            except Exception:
                pass
    q = f"""
    PREFIX drift: <{DRIFT}>
    PREFIX owl: <{OWL}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?t ?label ?qid ?date ?cat WHERE {{
      ?t a drift:TriggerEvent ; owl:sameAs ?qid .
      FILTER(STRSTARTS(STR(?qid), "{WD_ENTITY}Q"))
      OPTIONAL {{ ?t rdfs:label ?label }}
      OPTIONAL {{ ?t drift:eventDate ?date }}
      OPTIONAL {{ ?t drift:triggerCategory ?cat }}
    }} ORDER BY ?t
    """
    rows: dict[str, dict] = {}
    for r in g.query(q):
        iri = str(r.t)
        qid = str(r.qid).rsplit("/", 1)[-1]
        # one trigger may (rarely) carry two sameAs; keep the first Q-item seen.
        if iri in rows:
            continue
        rows[iri] = {
            "triggerId": iri,
            "slug": iri.rsplit("/", 1)[-1],
            "label": str(r.label) if r.label else "",
            "qid": qid,
            "eventDate": _clean_date(str(r.date)) if r.date else None,
            "category": str(r.cat).rsplit("#", 1)[-1] if r.cat else None,
        }
    return list(rows.values())


def _clean_date(s: str) -> str:
    """Normalise an xsd:gYear / xsd:date literal to a plain string (strip ^^type)."""
    return s.split("^^")[0].strip().strip('"')


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="geocode + print, do not write")
    ap.add_argument("--limit", type=int, default=0, help="only first N triggers (debug)")
    args = ap.parse_args()

    triggers = load_qid_triggers()
    if args.limit:
        triggers = triggers[: args.limit]
    total = len(triggers)
    print(f"QID-linked triggers: {total}", file=sys.stderr)

    located: list[dict] = []
    source_counts: dict[str, int] = {}
    for i, trig in enumerate(triggers, 1):
        res = coord_for_qid(trig["qid"])
        if res is None:
            print(f"[{i}/{total}] --  {trig['slug']} ({trig['qid']})", file=sys.stderr)
            continue
        lat, lon, src = res
        source_counts[src] = source_counts.get(src, 0) + 1
        located.append(
            {
                "triggerId": trig["triggerId"],
                "label": trig["label"],
                "qid": trig["qid"],
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "eventDate": trig["eventDate"],
                "category": trig["category"],
                "coordSource": src,
            }
        )
        print(
            f"[{i}/{total}] OK  {trig['slug']} ({trig['qid']}) "
            f"-> {lat:.4f},{lon:.4f} [{src}]",
            file=sys.stderr,
        )

    located.sort(key=lambda d: d["triggerId"])
    n_located = len(located)
    n_without = total - n_located
    print(
        f"\nGeocoded {n_located}/{total} QID-linked triggers "
        f"({n_without} without coordinates).",
        file=sys.stderr,
    )
    for src in sorted(source_counts):
        print(f"  {src}: {source_counts[src]}", file=sys.stderr)

    out = {
        "generator": "scripts/fetch-trigger-coords.py",
        "source": "Wikidata (P625 coordinate location; P19/P159/P740 place fallback)",
        "qidLinkedTriggers": total,
        "withCoordinates": n_located,
        "withoutCoordinates": n_without,
        "coordSourceBreakdown": dict(sorted(source_counts.items())),
        "triggers": located,
    }

    if args.dry_run:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {n_located} located triggers -> {OUT_JSON.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
