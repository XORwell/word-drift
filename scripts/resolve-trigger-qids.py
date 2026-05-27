#!/usr/bin/env python3
"""
resolve-trigger-qids.py — resolve Wikidata QIDs for unlinked drift:TriggerEvent nodes.

Goal: raise Wikidata owl:sameAs coverage of trigger events, but ONLY with
high-confidence matches (honesty over coverage; a wrong QID is worse than none).

What it does
------------
1. Loads examples/ + data/ into one rdflib graph and finds every
   drift:TriggerEvent that has NO owl:sameAs, collecting label / description /
   eventDate / category.
2. For each, queries Wikidata (wbsearchentities action API, then the SPARQL
   endpoint for entity metadata) and scores candidates.
3. Accepts a candidate ONLY when the heuristic is confident (see score_candidate):
   the label/alias matches closely, the entity *kind* is consistent with a
   trigger (event / person / organisation / work / invention / movement / place),
   and, where the trigger carries a year, the entity's inception / point-in-time /
   date-of-birth is consistent with it.
4. Writes data/wikidata/trigger-links.ttl (sameAs triples only, reusing the
   existing trigger IRIs) and a JSON sidecar with the full decision log that the
   coverage report is built from.

Re-runnable & polite
---------------------
* All HTTP responses cached under .cache/wikidata/ (keyed by request hash);
  re-runs hit the cache and make zero network calls for already-seen lookups.
* A small delay between *uncached* network requests, descriptive User-Agent.

Cost: $0 (Wikidata is free, no LLM).

Usage
-----
    python scripts/resolve-trigger-qids.py            # resolve + write outputs
    python scripts/resolve-trigger-qids.py --dry-run  # resolve, print, no write
    python scripts/resolve-trigger-qids.py --limit 10 # only first N (debugging)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

warnings.simplefilter("ignore")

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache" / "wikidata"
OUT_TTL = ROOT / "data" / "wikidata" / "trigger-links.ttl"
OUT_JSON = ROOT / "data" / "wikidata" / "trigger-links.decisions.json"

DRIFT = "https://w3id.org/word-drift/ontology#"
OWL = "http://www.w3.org/2002/07/owl#"
WD_ENTITY = "http://www.wikidata.org/entity/"

USER_AGENT = "word-drift-research/0.4 (https://w3id.org/word-drift; research@nennemann.de)"
REQUEST_DELAY_S = 0.6  # polite gap between *uncached* network requests

# Wikidata "instance of" (P31) classes that are consistent with a trigger event.
# Each maps a broad kind -> set of acceptable root QIDs (resolved via subclass
# reasoning is overkill; we instead pull P31 of the candidate and check it sits
# under one of these by a direct-or-one-hop check at query time).
KIND_OK_HINTS = {
    "event": {
        "Q1190554",   # occurrence
        "Q1656682",   # event
        "Q1914636",   # activity
        "Q198",       # war
        "Q178561",    # battle
        "Q1261499",   # naval battle
        "Q830494",    # warfare? (battle subclass observed)
        "Q3839081",   # disaster
        "Q175331",    # demonstration
        "Q49773",     # social movement
        "Q49780",     # value / movement (Luddite)
        "Q208701",    # protest movement-ish
        "Q2738074",   # protest
        "Q124734",    # rebellion / uprising
        "Q12909644",  # military operation
        "Q98391050",  # nuclear weapon test series (Operation Crossroads)
        "Q4688003",   # strategic bombing (the Blitz)
        "Q645883",    # military operation (alt)
        "Q1827102",   # crusade
        "Q831663",    # military campaign
        "Q45382",     # coup d'état (March on Rome)
        "Q657449",    # insurrection
        "Q15631336",  # historical event / period
        "Q135976384", # edition of Olympic Games
        "Q14547231",  # Summer Olympics edition
        "Q16510064",  # sporting event
        "Q44512",     # epidemic
        "Q12198",     # plague (pandemic)
        "Q3241045",   # disease outbreak
    },
    "person": {"Q5"},  # human
    "org": {
        "Q43229",    # organization
        "Q4830453",  # business
        "Q783794",   # company
        "Q891723",   # public company
        "Q4438121",  # sports organization
        "Q48204",    # association
        "Q49773",    # social movement
        "Q2659904",  # government organization
        "Q1365916",  # dicastery (Roman Curia congregation)
        "Q1530022",  # religious organization
    },
    "work": {
        "Q571",        # book
        "Q7725634",    # literary work
        "Q47461344",   # written work
        "Q25379",      # play / drama
        "Q116476516",  # play (theatrical work / drama script)
        "Q1667921",    # novel sequence
        "Q8261",       # novel
        "Q386724",     # work
        "Q838948",     # work of art
        "Q47461344",   # written work
        "Q49084",      # short story
        "Q149537",     # treatise
        "Q1318295",    # narrative
        "Q105543609",  # musical work
    },
    "invention_product": {
        "Q11019",    # machine
        "Q1183543",  # device
        "Q42889",    # vehicle? generic
        "Q39546",    # tool
        "Q15401930", # product
        "Q2424752",  # product (alt)
        "Q205663",   # process
        "Q2424752",  # product
        "Q169336",   # mixture (chemical) e.g. resin
        "Q11173",    # chemical compound
        "Q12140",    # medication (aspirin)
        "Q1357761",  # invention? not standard
        "Q19603939", # patent? rarely linked directly
    },
    "place": {
        "Q486972",    # human settlement
        "Q515",       # city
        "Q3957",      # town
        "Q15273785",  # spa town
        "Q493522",    # spa / health resort
        "Q4946461",   # municipality of Belgium
        "Q82794",     # geographic region
        "Q1620908",   # historical region (Laconia)
        "Q62049",     # polis / ancient Greek city-state (Sparta)
        "Q148837",    # ancient city
        "Q15661340",  # ancient city (alt)
        "Q839954",    # archaeological site
        "Q1549591",   # big city
        "Q1093829",   # city in the United States
        "Q751708",    # village in the United States (Tuxedo Park, NY)
        "Q55237813",  # village of New York
        "Q23397",     # lake
        "Q42523",     # atoll
        "Q5119",      # capital
    },
}

# Triggers we deliberately DO NOT attempt to link: abstract semantic-process
# descriptions that have no real-world referent entity in Wikidata. Matched by
# substring on the trigger label (case-insensitive). Recorded as unresolved
# with the "abstract semantic process (no referent entity)" reason.
ABSTRACT_LABEL_MARKERS = [
    "polysemous extension",
    "semantic bleaching",
    "bleaching of",
    "weakening of",
    "revaluation of",
    "reversal of a",
    "pejoration by",
    "pejoration ueber",
    "ironic reversal",
    "hyperbolic bleaching",
    "intensifier",
    "downtoner",
    "negative collocation",
    "aufwertung",
    "generalisierung",
    "soziale generalisierung",
]


# --------------------------------------------------------------------------- #
# HTTP with on-disk cache
# --------------------------------------------------------------------------- #
def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def http_get_json(url: str) -> dict:
    """GET a URL returning JSON, cached on disk. Polite delay on cache miss."""
    cp = _cache_path(url)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(REQUEST_DELAY_S)
    return data


def wbsearch(label: str, language: str = "en", limit: int = 8) -> list[dict]:
    url = (
        "https://www.wikidata.org/w/api.php?action=wbsearchentities"
        f"&format=json&language={language}&uselang={language}"
        f"&type=item&limit={limit}&search={urllib.parse.quote(label)}"
    )
    try:
        data = http_get_json(url)
    except Exception as e:  # network/parse error -> no candidates
        return [{"_error": str(e)}]
    return data.get("search", [])


DATE_PROPS = ("P571", "P585", "P569", "P577", "P580", "P729")  # inception/PiT/DOB/pub/start


def entity_metadata(qid: str) -> dict:
    """Fetch P31 (instance of) QIDs and candidate years from date properties.

    Uses the wbgetentities action API (the WDQS SPARQL endpoint is, during the
    2024 wdqs outage, rate-limited to ~1 req/min and unusable at this volume).
    """
    url = (
        "https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&format=json&ids={qid}&props=claims&languages=en"
    )
    try:
        data = http_get_json(url)
    except Exception as e:
        return {"p31": set(), "years": set(), "_error": str(e)}
    ent = data.get("entities", {}).get(qid, {})
    claims = ent.get("claims", {})
    p31: set[str] = set()
    for st in claims.get("P31", []):
        dv = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(dv, dict) and "id" in dv:
            p31.add(dv["id"])
    years: set[int] = set()
    for prop in DATE_PROPS:
        for st in claims.get(prop, []):
            dv = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            t = dv.get("time") if isinstance(dv, dict) else None
            if not t:
                continue
            m = re.match(r"([+-]?\d{1,5})-", t)
            if m:
                try:
                    years.add(int(m.group(1)))
                except ValueError:
                    pass
    return {"p31": p31, "years": years}


# --------------------------------------------------------------------------- #
# graph loading
# --------------------------------------------------------------------------- #
def load_unlinked_triggers() -> list[dict]:
    import rdflib

    g = rdflib.Graph()
    for pat in ["examples/**/*.ttl", "data/**/*.ttl"]:
        for f in glob.glob(str(ROOT / pat), recursive=True):
            # never re-read our own output as input
            if Path(f).name in {OUT_TTL.name}:
                continue
            try:
                g.parse(f, format="turtle")
            except Exception:
                pass
    q = f"""
    PREFIX drift: <{DRIFT}>
    PREFIX owl: <{OWL}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dct: <http://purl.org/dc/terms/>
    SELECT ?t ?label ?desc ?date ?cat WHERE {{
      ?t a drift:TriggerEvent .
      FILTER NOT EXISTS {{ ?t owl:sameAs ?qq }}
      OPTIONAL {{ ?t rdfs:label ?label }}
      OPTIONAL {{ ?t dct:description ?desc }}
      OPTIONAL {{ ?t drift:eventDate ?date }}
      OPTIONAL {{ ?t drift:triggerCategory ?cat }}
    }} ORDER BY ?t
    """
    rows: dict[str, dict] = {}
    for r in g.query(q):
        iri = str(r.t)
        if iri in rows:
            continue
        label = str(r.label) if r.label else ""
        desc = str(r.desc) if r.desc else ""
        year = _parse_year(str(r.date)) if r.date else None
        # BC/BCE dates are stored as positive gYears in the source data; negate
        # so date comparison with Wikidata (signed years) is correct. Only flip
        # when the eventDate's own value is written as "<year> BC" in the text
        # (a bare "BC" elsewhere, e.g. a commemorated ancient battle in a modern
        # event's description, must not flip a modern trigger's year).
        if year is not None and year > 0 and _year_is_bc(year, label + " " + desc):
            year = -year
        rows[iri] = {
            "iri": iri,
            "slug": iri.rsplit("/", 1)[-1],
            "label": label,
            "desc": desc,
            "year": year,
            "cat": str(r.cat).rsplit("#", 1)[-1] if r.cat else "",
        }
    return list(rows.values())


_BC_RE = re.compile(r"\b(\d{1,4})\s*(bc|bce|b\.c\.|v\.?\s*chr\.?)\b", re.IGNORECASE)


def _is_bc(text: str) -> bool:
    """True if the text mentions any BC/BCE date (used in tests/debug only)."""
    return bool(_BC_RE.search(text))


def _year_is_bc(year: int, text: str) -> bool:
    """True only if THIS year value is written as '<year> BC' in the text.

    Allows fuzzy 'c. 621 BC' / 'around 387 BC' phrasing (the eventDate is the
    rounded value) by also accepting the year within +/-2 of a '<n> BC' mention.
    """
    for m in _BC_RE.finditer(text):
        n = int(m.group(1))
        if abs(n - year) <= 2:
            return True
    return False


def _parse_year(s: str) -> int | None:
    m = re.match(r"^(-?\d{1,4})", s)
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- #
# matching heuristic
# --------------------------------------------------------------------------- #
_STOP = {
    "the", "a", "an", "of", "and", "in", "at", "on", "to", "his", "her",
    "der", "die", "das", "und", "von", "im", "the", "for", "de",
}


def _norm(s: str) -> str:
    s = s.lower()
    # German digraph expansion first (so ö->oe, not o)
    s = (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))
    # strip all remaining diacritics (Laszlo Biro <-> László Bíró, Telemaque, etc.)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.replace("ł", "l").replace("ø", "o").replace("ð", "d")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if t and t not in _STOP and len(t) > 1}


def _label_overlap(query_terms: set[str], cand_label: str) -> float:
    ct = _tokens(cand_label)
    if not ct:
        return 0.0
    inter = query_terms & ct
    # Jaccard-ish but favouring candidate coverage (cand label fully contained)
    return len(inter) / max(1, len(ct))


def all_kind_qids() -> dict[str, str]:
    """Map every hint QID -> its kind label, for fast lookup."""
    m: dict[str, str] = {}
    for kind, qs in KIND_OK_HINTS.items():
        for q in qs:
            m[q] = kind
    return m


KIND_LOOKUP = all_kind_qids()


def score_candidate(trig: dict, cand: dict, meta: dict) -> tuple[float, str]:
    """Return (confidence 0..1, human-readable reason)."""
    cand_label = cand.get("label", "") or ""
    cand_desc = (cand.get("description", "") or "").lower()

    # search terms: prefer the SEARCH STRING actually used, fall back to label
    search_terms = trig.get("_search_terms") or _tokens(trig["label"])
    overlap = _label_overlap(search_terms, cand_label)

    # exact / near-exact label match is a strong signal. Treat "all search terms
    # contained in the candidate label" as equally strong, so a search for
    # "Samuel Morse" matches the canonical label "Samuel Finley Breese Morse"
    # (middle names) as well as a bare-name namesake — then prominence (rank)
    # picks the famous one.
    cand_terms = _tokens(cand_label)
    exact = (
        _norm(cand_label) == _norm(trig.get("_search_str", trig["label"]))
        or (search_terms and search_terms <= cand_terms)
    )

    # kind consistency
    p31 = meta.get("p31", set())
    kinds = {KIND_LOOKUP[q] for q in p31 if q in KIND_LOOKUP}
    kind_ok = bool(kinds)
    expected_kind = trig.get("_expected_kind", "")
    kind_match_expected = expected_kind in kinds if expected_kind else kind_ok

    # description sanity: reject obviously wrong kinds (Wikimedia disambig, etc.)
    bad_desc_markers = [
        "wikimedia disambiguation",
        "wikimedia category",
        "given name",
        "family name",
        "surname",
        "wikimedia list article",
        "scientific article",
        "genus of",
        "species of",
    ]
    desc_bad = any(m in cand_desc for m in bad_desc_markers)

    # Date consistency (only when both sides have a year). Asymmetric tolerance:
    # an entity whose date PRECEDES the trigger is fine and expected (a company
    # is founded, or a person born, well before the product/event the trigger
    # marks); a date AFTER the trigger, or wildly off, is suspicious. We compare
    # against the closest entity year.
    date_ok = None
    if trig.get("year") is not None and meta.get("years"):
        ty = trig["year"]
        tol_before = trig.get("_year_tol", 15)       # entity may predate trigger
        tol_after = min(20, trig.get("_year_tol", 15))  # entity rarely postdates
        def _ok(cy: int) -> bool:
            d = ty - cy  # >0 means entity is earlier than trigger
            return (-tol_after) <= d <= tol_before
        date_ok = any(_ok(cy) for cy in meta["years"])

    rank = trig.get("_rank", 0)

    # ---- scoring ----
    score = 0.0
    reasons = []
    if exact:
        score += 0.50
        reasons.append("exact/contained label match")
    else:
        score += 0.45 * overlap
        reasons.append(f"label overlap {overlap:.2f}")

    if expected_kind in ("person", "place"):
        # persons must be instance-of human (Q5); places must be a recognised
        # place class. This guard stops a same-name non-referent winning (a
        # mythological figure, or the painter "Lovis Corinth" for the city
        # Corinth, or a "Tuxedo Park" that is a person).
        if expected_kind in kinds:
            score += 0.25
            reasons.append(f"kind={expected_kind}")
        else:
            score -= 0.40
            reasons.append(f"NOT {expected_kind} ({expected_kind} expected)")
    elif expected_kind:
        if kind_match_expected:
            score += 0.25
            reasons.append(f"kind matches '{expected_kind}'")
        elif kind_ok:
            score += 0.05
            reasons.append(f"kind={'/'.join(sorted(kinds))}~'{expected_kind}'")
        else:
            # P31 not in our (incomplete) class lists. Not penalised: the curated
            # hint + exact-label + prominence below carry the confidence.
            reasons.append("kind unrecognised (not penalised)")
    elif kind_ok:
        score += 0.20
        reasons.append("kind=" + "/".join(sorted(kinds)))

    # For PLACES the entity date (a city's inception) is non-informative and
    # arbitrary relative to when the word was coined, so we neither reward nor
    # penalise it; the toponym is disambiguated by prominence (the city outranks
    # its eponymous university/football club). For persons/events/works/orgs a
    # date-consistent match must beat an equally-named UNDATED candidate (e.g.
    # the dated inventor "Laszlo Biro" over a same-name academy member), so the
    # date bonus exceeds the rank-0 bonus.
    if expected_kind != "place":
        if date_ok is True:
            score += 0.35
            reasons.append("date consistent")
        elif date_ok is False:
            score -= 0.45
            reasons.append("date INCONSISTENT")

    if desc_bad:
        score -= 0.6
        reasons.append("bad description kind")

    # Prominence: Wikidata search ranks famous entities first, so a curated hint
    # lands its intended referent at rank 0-1. The rank-0 bonus is large enough
    # that a rank-0 exact-label match alone (0.50 + 0.30) reaches threshold even
    # when we do not recognise the entity's P31 class, while obscure same-name
    # entities at lower ranks (a progamer "Plato", an unrelated "Laszlo Biro")
    # cannot reach it without also matching kind and date.
    rank_bonus = max(0.0, 0.30 - 0.10 * rank)
    if rank_bonus:
        score += rank_bonus
        reasons.append(f"rank{rank}+{rank_bonus:.2f}")

    # Return the RAW (un-clamped) score so candidate selection can distinguish a
    # date-consistent match (e.g. raw 1.20) from an undated same-name rank-0
    # match (raw 1.05); the caller clamps to [0,1] only for the reported
    # confidence. Floor at 0 to avoid negative noise.
    score = max(0.0, score)
    return score, "; ".join(reasons) + f" [{cand_desc[:60]}]"


# --------------------------------------------------------------------------- #
# Curated search hints, keyed by trigger slug (the last IRI segment).
#   value = (search_string, expected_kind, language)
# The script still RESOLVES and VERIFIES the QID at runtime against Wikidata
# (label overlap + P31 kind + inception/DOB date) — QIDs are never hardcoded.
# The hint only steers wbsearchentities to the right referent (the eponymous
# PERSON for eponyms, the EVENT for events, the WORK for literary triggers),
# because the descriptive trigger labels are useless as raw search strings.
# Triggers with no real-world referent (semantic-process triggers, vague
# discourse triggers) are intentionally absent and fall through to "unresolved".
# --------------------------------------------------------------------------- #
SEARCH_HINTS: dict[str, tuple[str, str, str]] = {
    # --- eponyms: link the PERSON ---
    "trigger-ampere-electrodynamics": ("Andre-Marie Ampere", "person", "en"),
    "trigger-bakelite-baekeland": ("Leo Baekeland", "person", "en"),
    "trigger-biro-patent": ("Laszlo Biro", "person", "en"),
    "trigger-braille-system": ("Louis Braille", "person", "en"),
    "trigger-cellophane-brand": ("Jacques Brandenberger", "person", "en"),
    "trigger-diesel-patent": ("Rudolf Diesel", "person", "en"),
    "trigger-galvanisieren-frogleg": ("Luigi Galvani", "person", "en"),
    "trigger-galvanize-frogleg": ("Luigi Galvani", "person", "en"),
    "trigger-gerrymander-redistricting": ("Elbridge Gerry", "person", "en"),
    "trigger-hertz-waves": ("Heinrich Hertz", "person", "en"),
    "trigger-linoleum-walton": ("Frederick Walton", "person", "en"),
    "trigger-mach-de-shockwave": ("Ernst Mach", "person", "en"),
    "trigger-maverick-cattle": ("Samuel Maverick", "person", "en"),
    "trigger-mesmerize-mesmer": ("Franz Mesmer", "person", "en"),
    "trigger-nicotine-tobacco": ("Jean Nicot", "person", "en"),
    "trigger-ohm-law": ("Georg Ohm", "person", "en"),
    "trigger-ohm-de-law": ("Georg Ohm", "person", "en"),
    "trigger-pasteurize-heat": ("Louis Pasteur", "person", "en"),
    "trigger-roentgen-discovery": ("Wilhelm Roentgen", "person", "en"),
    "trigger-saxophone-patent": ("Adolphe Sax", "person", "en"),
    "trigger-shrapnel-shell": ("Henry Shrapnel", "person", "en"),
    "trigger-volt-pile": ("Alessandro Volta", "person", "en"),
    "trigger-watt-engine": ("James Watt", "person", "en"),
    "trigger-boykott-landleague": ("Charles Boycott", "person", "en"),
    # NB: sandwich-earl (John Montagu, 4th Earl of Sandwich) intentionally NOT
    # linked: a bare "John Montagu" search returns several contemporaneous
    # namesakes (naval officer, colonial secretary, 7th Earl) that all pass the
    # person+date heuristic, so no single confident referent. Left unresolved.
    "trigger-silhouette-minister": ("Etienne de Silhouette", "person", "en"),
    "trigger-bowdlerize-shakespeare": ("Thomas Bowdler", "person", "en"),
    "trigger-quisling-invasion": ("Vidkun Quisling", "person", "en"),
    "trigger-vandalismus-gregoire": ("Henri Gregoire", "person", "en"),
    "trigger-guillotine-revolution": ("Joseph-Ignace Guillotin", "person", "en"),
    "trigger-guy-gunpowder": ("Guy Fawkes", "person", "en"),
    "trigger-morse-code-telegraph": ("Samuel Morse", "person", "en"),
    "trigger-akademie-plato": ("Plato", "person", "en"),
    "trigger-philippic-demosthenes": ("Demosthenes", "person", "en"),
    "trigger-machiavellian-principe": ("Niccolo Machiavelli", "person", "en"),
    # --- events / occurrences: link the EVENT ---
    "trigger-bikini-tests": ("Operation Crossroads", "event", "en"),
    "trigger-blitz-london": ("The Blitz", "event", "en"),
    "trigger-marathon-olympics": ("1896 Summer Olympics", "event", "en"),
    "trigger-luddite-uprising": ("Luddite", "event", "en"),
    "trigger-kamikaze-leyte": ("Battle of Leyte Gulf", "event", "en"),
    "trigger-ketzer-albigensian": ("Albigensian Crusade", "event", "en"),
    "trigger-gfds-ampel-aus-2024": ("2024 German government crisis", "event", "en"),
    # --- works / texts: link the WORK ---
    "trigger-frankenstein-shelley": ("Frankenstein", "work", "en"),
    "trigger-orwellian-1984": ("Nineteen Eighty-Four", "work", "en"),
    "trigger-yahoo-gulliver": ("Gulliver's Travels", "work", "en"),
    "trigger-quixotic-cervantes": ("Don Quixote", "work", "en"),
    "trigger-gargantuan-rabelais": ("Gargantua and Pantagruel", "work", "en"),
    "trigger-robot-rur": ("R.U.R.", "work", "en"),
    "trigger-mentor-telemaque": ("Les Aventures de Telemaque", "work", "en"),
    "trigger-malapropism-rivals": ("The Rivals", "work", "en"),
    # --- places: link the PLACE (only where the toponym IS the referent) ---
    "trigger-spa-town": ("Spa", "place", "en"),
    # --- organisations ---
    "trigger-propaganda-congregatio": ("Congregation for the Evangelization of Peoples", "org", "en"),
    # ----- second batch: further high-confidence eponyms / events / works ----- #
    # eponymous persons (link the PERSON)
    "trigger-zeppelin-lz1": ("Ferdinand von Zeppelin", "person", "en"),
    "trigger-mausoleum-halicarnassus": ("Mausolus", "person", "en"),
    "trigger-kafkaesque-prozess": ("Franz Kafka", "person", "en"),
    "trigger-klasse-marx": ("Karl Marx", "person", "en"),
    "trigger-narcissism-coinage": ("Havelock Ellis", "person", "en"),
    # NB: mythological eponyms (Pan/panic, Nemesis, Tantalus/tantalize,
    # Heracles/herculean, Sappho/lesbian, Draco/draconian) are intentionally
    # NOT linked: their canonical Wikidata items are not instance-of human
    # (mythological figure / deity), so the person heuristic cannot tell the
    # famous deity from a modern human namesake. Left unresolved (honesty).
    # NB: spartan-sparta / laconic-sparta intentionally NOT linked. A bare
    # "Sparta"/"Laconia" search surfaces same-name US towns (Sparta NC, Laconia
    # NH) that pass the place heuristic, and Greece-qualified searches return no
    # candidates from wbsearchentities, so no confident single referent. Left
    # unresolved (honesty over coverage).
    # events / occurrences (link the EVENT)
    "trigger-fascism-mussolini": ("March on Rome", "event", "en"),
    # works / texts (link the WORK)
    "trigger-chauvinismus-play": ("La cocarde tricolore", "work", "en"),

    # ----- third batch: WWI events, toponyms, originating companies/persons -- #
    # First World War triggers -> the war itself (Q361)
    "trigger-etappe-wwi": ("World War I", "event", "en"),
    "trigger-front-wwi": ("World War I", "event", "en"),
    "trigger-schuetzengraben-wwi": ("World War I", "event", "en"),
    "trigger-trommelfeuer-wwi": ("World War I", "event", "en"),
    # toponyms -> the PLACE the word is named after
    "trigger-jeans-genoa": ("Genoa", "place", "en"),
    "trigger-denim-nimes": ("Nimes", "place", "en"),
    "trigger-cologne-eau": ("Cologne", "place", "en"),
    "trigger-currant-corinth": ("Corinth", "place", "en"),
    "trigger-damast-damaskus": ("Damascus", "place", "en"),
    "trigger-rugby-school": ("Rugby School", "org", "en"),
    "trigger-tuxedo-park": ("Tuxedo Park", "place", "en"),
    # eponymous persons / titles
    "trigger-kaiser-augustus": ("Augustus", "person", "en"),
    "trigger-atlas-mercator": ("Gerardus Mercator", "person", "en"),
    # originating companies (the trigger is "Company launches/markets X")
    "trigger-aspirin-bayer": ("Bayer", "org", "en"),
    "trigger-escalator-otis": ("Otis Worldwide", "org", "en"),
    "trigger-kleenex-kc": ("Kimberly-Clark", "org", "en"),
    "trigger-nylon-dupont": ("DuPont", "org", "en"),
    "trigger-labello-de-brand": ("Beiersdorf", "org", "en"),
    "trigger-zipper-goodrich": ("Goodrich Corporation", "org", "en"),
    # inventions / brand-name products NOT linked when the trigger word IS the
    # brand and no clean company/person referent exists (granola, thermos, uhu,
    # tempo, foehn, xerox-the-machine, ...): brand-vs-generic ambiguity, left
    # unresolved on purpose (honesty over coverage).
}


def search_plan(trig: dict) -> list[tuple[str, str, int, str]]:
    """Yield (search_str, language, year_tol, expected_kind) attempts, best first.

    expected_kind: one of KIND_OK_HINTS keys, or "" for no kind constraint.
    """
    plans: list[tuple[str, str, int, str]] = []
    hint = SEARCH_HINTS.get(trig["slug"])
    if hint:
        search_str, kind, lang = hint
        # Year tolerance is "how far the entity's date may PRECEDE the trigger":
        #  - person: DOB decades before the eponymous act (born ~1775, acts 1820)
        #  - org:    company founded long before the product/brand launch
        #  - place:  city inception can be centuries/millennia before the word
        #            (Genoa, Damascus); the place date is non-informative, so
        #            disable the date penalty by making the window very wide
        #  - event/work: the date IS the trigger date, keep it tight
        tol = {"person": 90, "org": 600, "place": 6000}.get(kind, 12)
        plans.append((search_str, lang, tol, kind))
        return plans
    # no curated hint -> do not guess from the descriptive label (too noisy).
    return plans


ACCEPT_THRESHOLD = 0.80


def resolve_one(trig: dict) -> dict:
    """Resolve a single trigger -> decision dict."""
    label_l = trig["label"].lower()
    for marker in ABSTRACT_LABEL_MARKERS:
        if marker in label_l:
            return {
                **_slim(trig),
                "status": "unresolved",
                "reason": "abstract semantic process (no real-world referent entity in Wikidata)",
            }

    plans = search_plan(trig)
    if not plans:
        return {
            **_slim(trig),
            "status": "unresolved",
            "reason": "no curated Wikidata referent (descriptive/discourse trigger; "
            "no single real-world entity to link with confidence)",
        }

    best = None  # (score, qid, cand_label, reason, search_str)
    tried = []
    for search_str, lang, tol, expected_kind in plans:
        trig["_search_terms"] = _tokens(search_str)
        trig["_search_str"] = search_str
        trig["_year_tol"] = tol
        trig["_expected_kind"] = expected_kind
        cands = wbsearch(search_str, language=lang)
        if cands and "_error" in cands[0]:
            tried.append(f"'{search_str}': API error {cands[0]['_error']}")
            continue
        for rank, cand in enumerate(cands[:6]):
            qid = cand.get("id")
            if not qid or not qid.startswith("Q"):
                continue
            trig["_rank"] = rank
            meta = entity_metadata(qid)
            score, reason = score_candidate(trig, cand, meta)
            if best is None or score > best[0]:
                best = (score, qid, cand.get("label", ""), reason, search_str)
        tried.append(f"'{search_str}': {len(cands)} candidates")

    if best and best[0] >= ACCEPT_THRESHOLD:
        return {
            **_slim(trig),
            "status": "resolved",
            "qid": best[1],
            "matched_label": best[2],
            "confidence": round(min(1.0, best[0]), 3),  # clamp for reporting
            "reason": best[3],
        }
    # not confident enough
    detail = (
        f"best candidate {best[1]} ('{best[2]}') scored {best[0]:.2f} "
        f"< {ACCEPT_THRESHOLD} ({best[3]})"
        if best
        else "no candidates returned"
    )
    return {
        **_slim(trig),
        "status": "unresolved",
        "reason": f"no high-confidence match: {detail}",
        "tried": tried,
    }


def _slim(trig: dict) -> dict:
    return {
        "iri": trig["iri"],
        "slug": trig["slug"],
        "label": trig["label"],
        "year": trig["year"],
        "cat": trig["cat"],
    }


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #
TTL_HEADER = """\
# data/wikidata/trigger-links.ttl
# Auto-generated by scripts/resolve-trigger-qids.py: owl:sameAs links from
# drift:TriggerEvent nodes to Wikidata Q-items. Only high-confidence matches
# are emitted (see data/reports/wikidata-coverage.md for method + caveats).
# These triples ONLY add owl:sameAs to existing trigger IRIs; they do not
# redefine the trigger. QIDs were matched by heuristic, not hand-verified;
# a human spot-check is advisable before publication.

@prefix wdr: <https://w3id.org/word-drift/resource/> .
@prefix wd:  <http://www.wikidata.org/entity/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

"""


def write_ttl(decisions: list[dict]) -> int:
    resolved = [d for d in decisions if d["status"] == "resolved"]
    resolved.sort(key=lambda d: d["slug"])
    lines = [TTL_HEADER]
    for d in resolved:
        local = d["iri"].rsplit("/", 1)[-1]
        # sanitize comment text: the project lint forbids em/en dashes anywhere
        # in .ttl, and Wikidata labels/descriptions may contain them.
        comment = f"{d['label']}  (conf {d['confidence']}; matched '{d['matched_label']}')"
        comment = comment.replace("—", "-").replace("–", "-")
        lines.append(f"# {comment}\nwdr:{local} owl:sameAs wd:{d['qid']} .\n")
    OUT_TTL.parent.mkdir(parents=True, exist_ok=True)
    OUT_TTL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(resolved)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="resolve + print, do not write files")
    ap.add_argument("--limit", type=int, default=0, help="only process first N triggers (debug)")
    args = ap.parse_args()

    triggers = load_unlinked_triggers()
    if args.limit:
        triggers = triggers[: args.limit]
    print(f"Unlinked triggers to resolve: {len(triggers)}", file=sys.stderr)

    decisions = []
    for i, trig in enumerate(triggers, 1):
        d = resolve_one(trig)
        decisions.append(d)
        flag = "OK " if d["status"] == "resolved" else "-- "
        extra = f"-> {d.get('qid')} ({d.get('confidence')})" if d["status"] == "resolved" else ""
        print(f"[{i}/{len(triggers)}] {flag}{trig['slug']} {extra}", file=sys.stderr)

    n_res = sum(1 for d in decisions if d["status"] == "resolved")
    print(f"\nResolved {n_res}/{len(triggers)} with confidence >= {ACCEPT_THRESHOLD}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(decisions, indent=2, ensure_ascii=False))
        return 0

    n_written = write_ttl(decisions)
    OUT_JSON.write_text(json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {n_written} sameAs triples -> {OUT_TTL.relative_to(ROOT)}", file=sys.stderr)
    print(f"Decision log -> {OUT_JSON.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
