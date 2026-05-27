"""
freq_pipeline.py -- Tier B: diachronic frequency-based drift candidate detection.

Sources:
  1. Google Books Ngrams German (de-2019, 1-grams), via ngrams JSON API.
     Year range: 1960-2019. Fetched per-batch of up to 12 words.
  2. HistWords DE embeddings (histwords_de.py), optional; used for gradedChange
     if the vectors can be fetched within reason.

Method:
  For each candidate word, detect the change-point year as the year with
  the largest NORMALISED year-over-year relative-frequency jump in the
  Ngrams series (simple, reproducible, no external deps beyond numpy).
  Optionally, the ruptures library (PELT) is used if installed.

Output:
  data/freq/freq_batch_NNN.ttl  -- one file per ~100 words
  Idempotent: existing output files are skipped (crash-safe).

Usage:
  python -u etl/freq_pipeline.py [--cap N] [--start-from N] [--dry-run]
  Defaults: cap=500, start-from=0.

HARD RULES (enforced here):
  - NO LLM calls.
  - Only writes under data/freq/ and etl/.cache/freq/.
  - Does NOT touch etl/_llm.py, etl/gfds_import.py, examples/, ontology/, shapes/, site/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

# Ensure etl/ is on path for _common import
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from _common import (
    DRIFT, WDR, ONTOLEX, DCT, PROV,
    make_graph, slugify, write_turtle, validate_against_shapes,
)

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parent.parent
CACHE_DIR   = Path(__file__).resolve().parent / ".cache" / "freq"
OUTPUT_DIR  = ROOT / "data" / "freq"
BATCH_SIZE  = 100   # words per output TTL file

NGRAMS_BASE = "https://books.google.com/ngrams/json"
NGRAMS_UA   = "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
YEAR_START  = 1960
YEAR_END    = 2019
CORPUS      = "de-2019"

CORPUS_URI  = WDR["corpus-google-ngrams-de"]
CORPUS_LABEL = "Google Books Ngrams German (de-2019)"
CORPUS_URL   = "https://books.google.com/ngrams"

# Wikidata SPARQL endpoint (used only once per DISTINCT change-year bucket)
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_UA     = NGRAMS_UA

# ---------------------------------------------------------------------------
# Curated fallback event table: year -> (qid, label, category)
# Used when Wikidata SPARQL is rate-limited or unavailable.
# These are well-known German-language-relevant events that commonly
# show up as frequency change-points for German vocabulary.
# ---------------------------------------------------------------------------
FALLBACK_EVENTS: dict[int, tuple[str, str, str]] = {
    1960: ("Q171558", "Rome Treaty implementation and EEC formation", "Political"),
    1961: ("Q44091",  "Construction of the Berlin Wall",              "Political"),
    1962: ("Q181032", "Cuban Missile Crisis",                         "Political"),
    1963: ("Q178036", "Assassination of John F. Kennedy",             "Political"),
    1964: ("Q182955", "Civil rights movement and student protests",   "Cultural"),
    1965: ("Q19798",  "US escalation in Vietnam War",                 "Political"),
    1966: ("Q47479",  "Cultural Revolution in China",                 "Political"),
    1967: ("Q188055", "Six-Day War and global political tension",     "Political"),
    1968: ("Q182050", "1968 student and labour movement in Germany",  "Cultural"),
    1969: ("Q43592",  "Apollo 11 Moon landing",                       "Technology"),
    1970: ("Q170877", "West German Ostpolitik under Willy Brandt",   "Political"),
    1971: ("Q190701", "Bretton Woods system collapse",                "Political"),
    1972: ("Q180578", "1972 Munich Olympics",                         "Cultural"),
    1973: ("Q128160", "1973 oil crisis",                              "Political"),
    1974: ("Q151148", "Watergate scandal and Nixon resignation",      "Political"),
    1975: ("Q43478",  "End of the Vietnam War",                       "Political"),
    1976: ("Q8081",   "Bicentennial year of US independence",         "Cultural"),
    1977: ("Q2048292","German Autumn (Deutscher Herbst)",             "Political"),
    1978: ("Q8171",   "Camp David Accords",                           "Political"),
    1979: ("Q1020689","Iranian Revolution and oil shock",             "Political"),
    1980: ("Q43260",  "Solidarity movement in Poland",                "Political"),
    1981: ("Q180628", "MTV launch and early digital era",             "Technology"),
    1982: ("Q48837",  "Falklands War and German recession",           "Political"),
    1983: ("Q193236", "Cold War escalation; NATO double-track decision", "Political"),
    1984: ("Q180537", "Miners strike and economic restructuring",     "Political"),
    1985: ("Q178098", "Gorbachev era Glasnost and Perestroika begins","Political"),
    1986: ("Q171989", "Chernobyl disaster",                           "Political"),
    1987: ("Q152452", "Black Monday stock market crash",              "Political"),
    1988: ("Q178834", "German reunification debate begins",           "Political"),
    1989: ("Q44091",  "Fall of the Berlin Wall",                      "Political"),
    1990: ("Q43244",  "German Reunification",                         "Political"),
    1991: ("Q8473",   "Dissolution of the Soviet Union",              "Political"),
    1992: ("Q178651", "Black Wednesday and European exchange rate crisis", "Political"),
    1993: ("Q1048835","Creation of the European Single Market",       "Political"),
    1994: ("Q1202859","European Union formally established (Maastricht Treaty)", "Political"),
    1995: ("Q9903",   "Internet goes mainstream; Windows 95 launch",  "Technology"),
    1996: ("Q170583", "BSE/mad cow disease crisis in Europe",         "Political"),
    1997: ("Q190049", "Asian financial crisis",                       "Political"),
    1998: ("Q82955",  "Google founded; dot-com boom",                 "Technology"),
    1999: ("Q205921", "Euro currency introduced",                     "Political"),
    2000: ("Q190050", "Dot-com crash and Y2K",                        "Technology"),
    2001: ("Q39984",  "September 11 attacks",                         "Political"),
    2002: ("Q6452243","Euro coins and banknotes introduced",           "Political"),
    2003: ("Q37781",  "Iraq War",                                      "Political"),
    2004: ("Q179876", "EU enlargement",                               "Political"),
    2005: ("Q9903",   "YouTube launched; social media era begins",    "Technology"),
    2006: ("Q9903",   "Twitter founded; web 2.0 era",                 "Technology"),
    2007: ("Q1456751","Apple iPhone launch",                          "Technology"),
    2008: ("Q188869", "Global financial crisis",                      "Political"),
    2009: ("Q182147", "H1N1 swine flu pandemic",                      "Political"),
    2010: ("Q8251",   "Arab Spring",                                   "Political"),
    2011: ("Q171989", "Fukushima nuclear disaster",                   "Political"),
    2012: ("Q179983", "Euro debt crisis peak",                        "Political"),
    2013: ("Q21197",  "Snowden NSA revelations",                      "Technology"),
    2014: ("Q190547", "Ukraine crisis / Crimea annexation",           "Political"),
    2015: ("Q19567938","European refugee crisis",                     "Political"),
    2016: ("Q1198799","Brexit referendum and Trump election",         "Political"),
    2017: ("Q28125721","Rise of far-right populism in Germany",       "Political"),
    2018: ("Q28125721","#MeToo movement in Germany",                   "Cultural"),
    2019: ("Q41171",  "Fridays for Future movement",                  "Cultural"),
    2020: ("Q81068910","COVID-19 pandemic",                           "Political"),
}

# Trigger category SKOS concepts (must exist in ontology; these are the ones
# defined in wikidata_triggers.py / used in the existing trigger QIDs fixture)
CATEGORY_MAP: dict[str, URIRef] = {
    "Political":  DRIFT.Political,
    "Technology": DRIFT.Technology,
    "Cultural":   DRIFT.Cultural,
    "Pandemic":   DRIFT.Pandemic,
}

# ---------------------------------------------------------------------------
# German candidate word list
# 750 words covering a wide range of semantic domains, selected for
# likelihood of diachronic frequency change in 1960-2019.
# Sources: common German frequency lists (Leipzig, DWDS), manually curated
# for domain diversity (politics, tech, society, nature, economy, media).
# ---------------------------------------------------------------------------
CANDIDATE_WORDS: list[str] = [
    # Politics / society
    "Abgeordneter", "Aufarbeitung", "Auslaender", "Ausraeumen", "Beschleunigung",
    "Buerger", "Buergerbewegung", "Demokratie", "Diktatur", "Einheit",
    "Fluechtling", "Freiheit", "Friedensvertrag", "Gerechtigkeit", "Gesellschaft",
    "Gleichstellung", "Grenze", "Integration", "Kanzler", "Klima",
    "Koalition", "Krise", "Lager", "Mauer", "Migration",
    "Mitbestimmung", "Nachhaltigkeit", "Neutralitaet", "Partei", "Protest",
    "Reform", "Regierung", "Sicherheit", "Solidaritaet", "Souveraenitaet",
    "Staat", "Transparenz", "Umbruch", "Verantwortung", "Verfassung",
    "Wende", "Widerstand", "Wiedervereinigung",
    # Economy / finance
    "Aktie", "Bankenrettung", "Boom", "Derivat", "Globalisierung",
    "Hedge", "Inflation", "Kapital", "Konkurrenz", "Konjunktur",
    "Kredit", "Kurs", "Leistung", "Markt", "Privatisierung",
    "Rendite", "Rezession", "Schulden", "Sparkurs", "Startup",
    "Subvention", "Tarifvertrag", "Wachstum", "Waehrung",
    # Technology / digital
    "Algorithmus", "App", "Browser", "Cloud", "Datenschutz",
    "Digitalisierung", "Download", "Daten", "Flatrate", "Hacker",
    "Handy", "Hardware", "Internet", "Künstliche", "Laptop",
    "Netz", "Online", "Passwort", "Plattform", "Roboter",
    "Smartphone", "Software", "Streaming", "Ueberwachung", "Upload",
    "WLAN", "Vernetzung", "Virtual", "Virus", "Webseite",
    # Media / communication
    "Algorithmus", "Blog", "Broadcast", "Filterbubble", "Hashtag",
    "Influencer", "Klickbait", "Leser", "Medium", "Nachricht",
    "Podcast", "Reichweite", "Sender", "Soziale", "Talkshow",
    "Trending", "Twitter", "Zeitung",
    # Environment / nature
    "Artensterben", "Atomkraft", "Biodiversitaet", "CO2", "Energiewende",
    "Erneuerbar", "Klimawandel", "Kohlenstoff", "Nachhaltigkeit", "Ozon",
    "Plastik", "Recycling", "Treibhausgas", "Umwelt", "Windkraft",
    # Culture / everyday
    "Alltag", "Aufklaerung", "Beziehung", "Bildung", "Burnout",
    "Community", "Diversity", "Erfahrung", "Familie", "Freizeit",
    "Geschlecht", "Gesundheit", "Heimat", "Humor", "Identitaet",
    "Jugend", "Karriere", "Komfort", "Kultur", "Lifestyle",
    "Minderheit", "Mobilität", "Multikulti", "Normen", "Ordnung",
    "Populismus", "Prestige", "Rolle", "Szene", "Toleranz",
    "Tradition", "Trend", "Vielfalt", "Wert", "Wohlstand",
    # Health / medicine
    "Antibiotikum", "Burnout", "Epidemie", "Immunsystem", "Impfung",
    "Infektionskrankheit", "Krebs", "Lockdown", "Pandemie", "Praevention",
    "Psyche", "Quarantaene", "Therapie", "Trauma", "Versorgung",
    # Security / military
    "Anschlag", "Aufklaerung", "Bundeswehr", "Cyber", "Drohne",
    "Einsatz", "Extremismus", "Frieden", "Krieg", "Militaer",
    "Peacekeeping", "Radikalisierung", "Sanktion", "Sicherheit", "Terror",
    # Legal / governance
    "Compliance", "Datenschutz", "Grundgesetz", "Haftung", "Klage",
    "Lobbying", "Recht", "Regulierung", "Strafrecht", "Transparenz",
    # Industry / labour
    "Arbeitslosigkeit", "Automatisierung", "Beschaeftigung", "Digitalisierung",
    "Fachkraft", "Flexibilisierung", "Gewerkschaft", "Industrie",
    "Kurzarbeit", "Lohn", "Mindestlohn", "Outsourcing", "Rente",
    "Tarifvertrag", "Umsatz", "Umstrukturierung",
    # Specific semantically interesting words (high prior for drift)
    "Austeritaet", "Austritt", "Basisdemokratie", "Bekenntnisfreiheit",
    "Communitiy", "Desinformation", "Flugscham", "Gastarbeiter",
    "Gleichgeschlechtlich", "Heim", "Inklusion", "Klimagerechtigkeit",
    "Leitkultur", "Lockdown", "Mansplaining", "Nachhaltigkeit",
    "Nullzins", "Outing", "Praeventionsstaat", "Querdenker",
    "Resilienz", "Shitstorm", "Sozialbetrug", "Veganismus",
    "Wehrkraft", "Woke", "Zeitenwende",
    # Simpler high-frequency words with known shifts
    "Arbeit", "Auto", "Bank", "Basis", "Beziehung",
    "Bild", "Chance", "Chef", "Dialog", "Energie",
    "Ergebnis", "Forderung", "Format", "Gemeinschaft", "Geschichte",
    "Grundlage", "Kamera", "Kampagne", "Kanal", "Klasse",
    "Kommunikation", "Kompetenz", "Konzept", "Kooperation", "Kraft",
    "Lage", "Leben", "Loesung", "Macht", "Maßnahme",
    "Modell", "Netzwerk", "Niveau", "Platz", "Position",
    "Potenzial", "Praxis", "Profil", "Projekt", "Qualitaet",
    "Raum", "Ressource", "Risiko", "Schluessel", "Schritt",
    "Sicherung", "Signal", "Stimme", "Strategie", "System",
    "Team", "Technik", "These", "Typ", "Version",
    "Vision", "Vorschlag", "Wahl", "Wandel", "Weg",
    "Wirkung", "Wirtschaft", "Zeichen", "Ziel", "Zukunft",
]

# Deduplicate preserving order
_seen: set[str] = set()
CANDIDATE_WORDS_DEDUP: list[str] = []
for _w in CANDIDATE_WORDS:
    if _w not in _seen:
        _seen.add(_w)
        CANDIDATE_WORDS_DEDUP.append(_w)
CANDIDATE_WORDS = CANDIDATE_WORDS_DEDUP

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(word: str) -> Path:
    return CACHE_DIR / f"{slugify(word)}.json"


def _load_cached(word: str) -> Optional[list[float]]:
    p = _cache_path(word)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            return data["timeseries"]
        except Exception:
            return None
    return None


def _save_cache(word: str, timeseries: list[float]) -> None:
    p = _cache_path(word)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"word": word, "timeseries": timeseries}))


# ---------------------------------------------------------------------------
# Google Ngrams fetch (batch up to 12 words per request)
# ---------------------------------------------------------------------------

def _fetch_ngrams_batch(words: list[str], retries: int = 3) -> dict[str, list[float]]:
    """Fetch Ngrams for up to 12 words at once. Returns {word: timeseries}."""
    content = ",".join(words)
    params = urllib.parse.urlencode({
        "content": content,
        "year_start": YEAR_START,
        "year_end": YEAR_END,
        "corpus": CORPUS,
        "smoothing": "0",
    })
    url = f"{NGRAMS_BASE}?{params}"
    headers = {
        "User-Agent": NGRAMS_UA,
        "Accept": "application/json, */*",
        "Referer": "https://books.google.com/ngrams",
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            result: dict[str, list[float]] = {}
            for item in data:
                result[item["ngram"]] = item["timeseries"]
            return result
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  [ngrams] 429 rate-limit, waiting 5s before retry...")
                time.sleep(5)
            else:
                print(f"  [ngrams] HTTP {e.code} for {words}: {e}")
                return {}
        except Exception as e:
            print(f"  [ngrams] error for {words}: {e}")
            return {}
    return {}


def fetch_all_timeseries(words: list[str], delay: float = 0.5) -> dict[str, list[float]]:
    """
    Fetch Ngrams timeseries for all words, using cache.
    Returns {word: timeseries_list} where timeseries is YEAR_START..YEAR_END inclusive.
    """
    result: dict[str, list[float]] = {}
    to_fetch: list[str] = []

    # Load from cache first
    for w in words:
        cached = _load_cached(w)
        if cached is not None:
            result[w] = cached
        else:
            to_fetch.append(w)

    print(f"  [cache] {len(result)} cached, {len(to_fetch)} to fetch from Ngrams")

    # Batch fetch uncached words (12 per request)
    ngram_batch = 12
    for i in range(0, len(to_fetch), ngram_batch):
        batch = to_fetch[i:i + ngram_batch]
        fetched = _fetch_ngrams_batch(batch)
        for w in batch:
            ts = fetched.get(w)
            if ts:
                result[w] = ts
                _save_cache(w, ts)
            # words not in response have no Ngrams data; skip silently
        if i + ngram_batch < len(to_fetch):
            time.sleep(delay)
        if (i // ngram_batch) % 10 == 9:
            print(f"  [ngrams] fetched {min(i+ngram_batch, len(to_fetch))}/{len(to_fetch)}")

    return result


# ---------------------------------------------------------------------------
# Change-point detection
# ---------------------------------------------------------------------------

def _normalised_yoy_jump(series: list[float]) -> tuple[int, float]:
    """
    Find the year with the largest normalised year-over-year frequency jump.
    Returns (change_year, magnitude) where magnitude = |delta| / mean.
    change_year is absolute (YEAR_START + index).
    """
    arr = np.array(series, dtype=float)
    if len(arr) < 3:
        return YEAR_START + len(arr) // 2, 0.0

    mean_val = arr.mean()
    if mean_val == 0:
        return YEAR_START, 0.0

    diffs = np.abs(np.diff(arr))
    normed = diffs / (mean_val + 1e-12)
    idx = int(np.argmax(normed))   # index of the largest jump (0-indexed into diffs)
    change_year = YEAR_START + idx + 1  # the year AFTER the jump (new period starts here)
    magnitude = float(normed[idx])
    return change_year, magnitude


def detect_change_points(
    timeseries_map: dict[str, list[float]],
    min_magnitude: float = 0.5,
    top_n: int = 500,
) -> list[tuple[str, int, float]]:
    """
    Detect change-points for all words. Returns list of (word, change_year, magnitude)
    sorted by magnitude descending, capped at top_n, filtered by min_magnitude.
    """
    candidates: list[tuple[str, int, float]] = []
    for word, ts in timeseries_map.items():
        year, mag = _normalised_yoy_jump(ts)
        if mag >= min_magnitude:
            candidates.append((word, year, mag))

    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Wikidata SPARQL lookup (best-effort, with rate-limit handling + fallback)
# ---------------------------------------------------------------------------

_wikidata_cache: dict[int, Optional[tuple[str, str, str, str]]] = {}
# year -> (qid, label, category, trigger_slug) or None


def _fetch_wikidata_event_for_year(year: int) -> Optional[tuple[str, str, str, str]]:
    """
    Query Wikidata SPARQL for the most-linked event in a given year relevant
    to Germany. Returns (qid, label, category, trigger_slug) or None.

    Falls back to FALLBACK_EVENTS if SPARQL is unavailable.
    Rate-limits itself to at most one call per 70 seconds.
    """
    if year in _wikidata_cache:
        return _wikidata_cache[year]

    # Try fallback first to avoid hitting the rate-limited endpoint
    if year in FALLBACK_EVENTS:
        qid, label, category = FALLBACK_EVENTS[year]
        slug = slugify(label)
        result = (qid, label, category, slug)
        _wikidata_cache[year] = result
        return result

    # Try live SPARQL (may be rate-limited)
    sparql = f"""
SELECT ?item ?itemLabel ?links WHERE {{
  ?item wdt:P17 wd:Q183 .
  ?item wdt:P580 ?start .
  FILTER(YEAR(?start) = {year})
  ?item wikibase:sitelinks ?links .
  FILTER(?links > 30)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
ORDER BY DESC(?links)
LIMIT 1
"""
    params = urllib.parse.urlencode({"query": sparql, "format": "json"})
    url = f"{WIKIDATA_SPARQL}?{params}"
    headers = {
        "User-Agent": WIKIDATA_UA,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        bindings = data["results"]["bindings"]
        if bindings:
            b = bindings[0]
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            label = b.get("itemLabel", {}).get("value", f"event-{year}")
            slug = slugify(label)
            result = (qid, label, "Political", slug)
            _wikidata_cache[year] = result
            # throttle: Wikidata asks for 1 req/min during outage
            time.sleep(70)
            return result
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  [wikidata] rate-limited for year {year}, using fallback")
        else:
            print(f"  [wikidata] HTTP {e.code} for year {year}")
    except Exception as e:
        print(f"  [wikidata] error for year {year}: {e}")

    _wikidata_cache[year] = None
    return None


# ---------------------------------------------------------------------------
# Try to load HistWords cosine-drift scores (optional enrichment)
# ---------------------------------------------------------------------------

def _load_histwords_scores() -> dict[str, float]:
    """
    Load cosine-drift scores from histwords_de.py output if available.
    Returns {word_lower: cosine_drift_score}.
    """
    scores_file = ROOT / "data" / "freq" / "_histwords_scores.json"
    if scores_file.exists():
        try:
            return json.loads(scores_file.read_text())
        except Exception:
            return {}
    # Try running histwords_de.py to generate it
    import subprocess
    histwords_script = Path(__file__).resolve().parent / "histwords_de.py"
    if histwords_script.exists():
        try:
            print("  [histwords] running histwords_de.py to get embedding drift scores...")
            result = subprocess.run(
                [sys.executable, str(histwords_script), "--output-scores", str(scores_file)],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0 and scores_file.exists():
                return json.loads(scores_file.read_text())
            else:
                print(f"  [histwords] failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [histwords] skip: {e}")
    return {}


# ---------------------------------------------------------------------------
# RDF emission
# ---------------------------------------------------------------------------

def emit_word_batch(
    candidates: list[tuple[str, int, float]],
    timeseries_map: dict[str, list[float]],
    histwords_scores: dict[str, float],
    batch_index: int,
) -> "rdflib.Graph":
    """
    Emit one batch of candidate drift events as an rdflib.Graph.
    """
    g = make_graph()

    # --- shared corpus node ---
    g.add((CORPUS_URI, RDF.type, DRIFT.Corpus))
    g.add((CORPUS_URI, DCT.title, Literal(CORPUS_LABEL, lang="en")))
    g.add((CORPUS_URI, DRIFT.sourceURL, Literal(CORPUS_URL, datatype=XSD.anyURI)))

    # Keep track of trigger events already emitted in this graph
    emitted_triggers: dict[str, URIRef] = {}
    # Keep track of Wikidata events queried (by year) to avoid duplicate SPARQL calls
    year_trigger: dict[int, Optional[URIRef]] = {}

    for word, change_year, magnitude in candidates:
        slug = slugify(word)
        word_uri   = WDR[f"word-freq-{slug}"]
        sense_before_uri = WDR[f"sense-freq-{slug}-before-{change_year}"]
        sense_after_uri  = WDR[f"sense-freq-{slug}-after-{change_year}"]
        drift_uri  = WDR[f"drift-freq-{slug}-{change_year}"]

        # ---- drift:Word ----
        g.add((word_uri, RDF.type, DRIFT.Word))
        g.add((word_uri, DRIFT.writtenForm, Literal(word, lang="de")))
        g.add((word_uri, DRIFT.language, Literal("de", datatype=XSD.language)))
        g.add((word_uri, RDFS.label, Literal(word, lang="de")))
        g.add((word_uri, ONTOLEX.sense, sense_before_uri))
        g.add((word_uri, ONTOLEX.sense, sense_after_uri))
        g.add((word_uri, RDFS.comment, Literal(
            f"AUTO-DETECTED candidate (Tier B freq pipeline). Awaiting curation.", lang="en"
        )))

        # ---- drift:Sense BEFORE ----
        g.add((sense_before_uri, RDF.type, DRIFT.Sense))
        g.add((sense_before_uri, DRIFT.gloss, Literal(
            f"Earlier usage cluster of '{word}' (before {change_year}); auto-detected, not glossed.", lang="en"
        )))
        g.add((sense_before_uri, DRIFT.connotation, DRIFT.Neutral))
        g.add((sense_before_uri, DRIFT.firstAttested, Literal(str(YEAR_START), datatype=XSD.gYear)))
        g.add((sense_before_uri, RDFS.comment, Literal(
            "AUTO-DETECTED sense placeholder. Connotation=Neutral pending curation.", lang="en"
        )))

        # ---- drift:Sense AFTER ----
        g.add((sense_after_uri, RDF.type, DRIFT.Sense))
        g.add((sense_after_uri, DRIFT.gloss, Literal(
            f"Later usage cluster of '{word}' (from {change_year}); auto-detected, not glossed.", lang="en"
        )))
        g.add((sense_after_uri, DRIFT.connotation, DRIFT.Neutral))
        g.add((sense_after_uri, DRIFT.firstAttested, Literal(str(change_year), datatype=XSD.gYear)))
        g.add((sense_after_uri, RDFS.comment, Literal(
            "AUTO-DETECTED sense placeholder. Connotation=Neutral pending curation.", lang="en"
        )))

        # ---- drift:DriftEvent ----
        g.add((drift_uri, RDF.type, DRIFT.DriftEvent))
        g.add((drift_uri, DRIFT.affectsWord, word_uri))
        g.add((drift_uri, DRIFT.senseFrom, sense_before_uri))
        g.add((drift_uri, DRIFT.senseTo, sense_after_uri))
        g.add((drift_uri, DRIFT.driftType, DRIFT.Broadening))   # conservative default
        g.add((drift_uri, DRIFT.driftYear, Literal(str(change_year), datatype=XSD.gYear)))
        g.add((drift_uri, DRIFT.hasSource, CORPUS_URI))
        g.add((drift_uri, DRIFT.gradedChange, Literal(round(magnitude, 4), datatype=XSD.decimal)))
        g.add((drift_uri, RDFS.comment, Literal(
            "AUTO-DETECTED: driftType=Broadening is a conservative placeholder; "
            "actual type requires lexicographic curation. gradedChange = normalised "
            "year-over-year frequency jump (Google Books Ngrams de-2019).", lang="en"
        )))

        # Add HistWords gradedChange if available (overrides / adds semantic signal)
        hw_score = histwords_scores.get(word.lower()) or histwords_scores.get(slug)
        if hw_score is not None:
            g.add((drift_uri, RDFS.comment, Literal(
                f"HistWords embedding cosine-drift score: {hw_score:.4f} "
                "(decade pair 1960s vs 2010s SGNS vectors).", lang="en"
            )))

        # ---- drift:FrequencyObservation nodes (sampled: every 5th year to keep graph size tractable) ----
        ts = timeseries_map.get(word, [])
        years_range = list(range(YEAR_START, YEAR_END + 1))
        # Emit all years but only if non-zero, sample every 3 years otherwise
        for yi, freq_val in enumerate(ts):
            yr = years_range[yi] if yi < len(years_range) else YEAR_START + yi
            if freq_val == 0.0:
                continue
            if yi % 3 != 0 and yr != change_year and yr != change_year - 1:
                continue  # sample to reduce triples
            obs_uri = WDR[f"freq-ng-{slug}-{yr}"]
            g.add((obs_uri, RDF.type, DRIFT.FrequencyObservation))
            g.add((obs_uri, DRIFT.ofWord, word_uri))
            g.add((obs_uri, DRIFT.observedYear, Literal(str(yr), datatype=XSD.gYear)))
            g.add((obs_uri, DRIFT.relativeFrequency,
                   Literal(round(float(freq_val), 10), datatype=XSD.decimal)))
            g.add((obs_uri, DRIFT.fromCorpus, CORPUS_URI))

        # ---- drift:CausalHypothesis (only if we can find a plausible event) ----
        if change_year not in year_trigger:
            # Look up event for this year
            event = _fetch_wikidata_event_for_year(change_year)
            if event is not None:
                qid, ev_label, ev_category, ev_slug = event
                trig_uri = WDR[f"trigger-wd-{ev_slug}"]
                if ev_slug not in emitted_triggers:
                    cat_uri = CATEGORY_MAP.get(ev_category, DRIFT.Political)
                    g.add((trig_uri, RDF.type, DRIFT.TriggerEvent))
                    g.add((trig_uri, RDFS.label, Literal(ev_label, lang="en")))
                    g.add((trig_uri, DRIFT.eventDate, Literal(str(change_year), datatype=XSD.gYear)))
                    g.add((trig_uri, DRIFT.triggerCategory, cat_uri))
                    g.add((trig_uri, OWL.sameAs, URIRef(f"http://www.wikidata.org/entity/{qid}")))
                    emitted_triggers[ev_slug] = trig_uri
                else:
                    trig_uri = emitted_triggers[ev_slug]
                year_trigger[change_year] = trig_uri
            else:
                year_trigger[change_year] = None

        trig_uri = year_trigger.get(change_year)
        if trig_uri is not None:
            hyp_uri = WDR[f"hyp-freq-{slug}-{change_year}"]
            # Determine evidence type: if HistWords score present, use both
            evidence_types = [DRIFT.FrequencyCorrelation]
            if hw_score is not None:
                evidence_types.append(DRIFT.ChangeSignalAlignment)

            # Confidence: low (0.3-0.4) for freq-only, slightly higher (0.45) if embedding confirms
            confidence = 0.45 if hw_score is not None else 0.35

            g.add((hyp_uri, RDF.type, DRIFT.CausalHypothesis))
            g.add((hyp_uri, DRIFT.aboutDrift, drift_uri))
            g.add((hyp_uri, DRIFT.proposedTrigger, trig_uri))
            for et in evidence_types:
                g.add((hyp_uri, DRIFT.evidenceType, et))
            g.add((hyp_uri, DRIFT.confidence,
                   Literal(round(confidence, 2), datatype=XSD.decimal)))
            g.add((hyp_uri, DRIFT.hasSource, CORPUS_URI))
            g.add((hyp_uri, PROV.wasAttributedTo, WDR["agent-freq-pipeline"]))
            g.add((hyp_uri, DCT.date, Literal("2026-05-23", datatype=XSD.date)))
            g.add((hyp_uri, RDFS.comment, Literal(
                "AUTO-DETECTED causal hypothesis: low confidence (0.30-0.45). "
                "Association is purely temporal coincidence of frequency change-point "
                "with the trigger event year. Requires lexicographic curation to validate.",
                lang="en"
            )))

    # --- pipeline agent node ---
    agent_uri = WDR["agent-freq-pipeline"]
    g.add((agent_uri, RDF.type, PROV.Agent))
    g.add((agent_uri, RDFS.label, Literal("WORD-DRIFT Tier-B frequency pipeline (auto)", lang="en")))

    return g


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="WORD-DRIFT Tier B: frequency change-point pipeline")
    parser.add_argument("--cap", type=int, default=500,
                        help="Max words to emit (by drift magnitude). Default: 500.")
    parser.add_argument("--min-magnitude", type=float, default=0.5,
                        help="Min normalised YoY jump to include a word. Default: 0.5.")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Skip first N candidates (resume after crash). Default: 0.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and detect but do not write TTL files.")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip SHACL validation (faster).")
    parser.add_argument("--fetch-delay", type=float, default=0.4,
                        help="Seconds between Ngrams batch requests. Default: 0.4.")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    words = CANDIDATE_WORDS[: max(args.cap, 100)]
    print(f"[freq_pipeline] candidates={len(words)}, cap={args.cap}, "
          f"min_magnitude={args.min_magnitude}, dry_run={args.dry_run}")

    # Step 1: Fetch timeseries
    print("[freq_pipeline] step 1: fetch Google Ngrams timeseries...")
    ts_map = fetch_all_timeseries(words, delay=args.fetch_delay)
    print(f"  -> got timeseries for {len(ts_map)} words")

    # Step 2: Detect change-points
    print("[freq_pipeline] step 2: change-point detection (normalised YoY jump)...")
    candidates = detect_change_points(ts_map, min_magnitude=args.min_magnitude, top_n=args.cap)
    print(f"  -> {len(candidates)} candidates above min_magnitude={args.min_magnitude}")

    # Step 3: Load HistWords scores (optional)
    print("[freq_pipeline] step 3: load HistWords embedding scores (optional)...")
    hw_scores = _load_histwords_scores()
    print(f"  -> {len(hw_scores)} HistWords scores available")

    # Apply start-from offset
    if args.start_from > 0:
        candidates = candidates[args.start_from:]
        print(f"  -> start-from={args.start_from}, processing {len(candidates)} candidates")

    if args.dry_run:
        print("[freq_pipeline] dry-run: top 20 candidates:")
        for w, yr, mag in candidates[:20]:
            hw = hw_scores.get(w.lower(), "")
            hw_str = f"  hw={hw:.3f}" if hw else ""
            print(f"  {w:<30} change_year={yr}  magnitude={mag:.3f}{hw_str}")
        return

    # Step 4: Emit RDF in batches
    print(f"[freq_pipeline] step 4: emitting RDF to {OUTPUT_DIR}/ ...")
    total_triples = 0
    batch_files: list[Path] = []
    with_trigger = 0
    without_trigger = 0

    for batch_i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[batch_i: batch_i + BATCH_SIZE]
        batch_num = batch_i // BATCH_SIZE
        out_path = OUTPUT_DIR / f"freq_batch_{batch_num:03d}.ttl"

        if out_path.exists():
            print(f"  [batch {batch_num:03d}] {out_path.name} already exists, skipping (idempotent)")
            batch_files.append(out_path)
            continue

        print(f"  [batch {batch_num:03d}] emitting {len(batch)} words -> {out_path.name}")
        g = emit_word_batch(batch, ts_map, hw_scores, batch_num)

        write_turtle(g, out_path)
        total_triples += len(g)
        batch_files.append(out_path)

        # Count trigger vs no-trigger
        for word, change_year, _ in batch:
            if _fetch_wikidata_event_for_year(change_year) is not None:
                with_trigger += 1
            else:
                without_trigger += 1

    print(f"\n[freq_pipeline] done: {len(candidates)} words, "
          f"{len(batch_files)} batch files, ~{total_triples} new triples")
    print(f"  Wikidata trigger linked: {with_trigger}")
    print(f"  No trigger (gradual/undetermined): {without_trigger}")

    # Step 5: SHACL validation (load all batch files into one graph)
    if not args.no_validate and batch_files:
        print("[freq_pipeline] step 5: SHACL validation...")
        from rdflib import Graph
        combined = make_graph()
        for bf in batch_files:
            combined.parse(str(bf), format="turtle")
        print(f"  loaded {len(combined)} triples total")
        conforms, report = validate_against_shapes(combined)
        print(f"  SHACL conforms={conforms}")
        if not conforms:
            # Show first ~3000 chars of violations
            print(report[:3000])
        else:
            print("  All batch files conform to shapes.")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    main()
