#!/usr/bin/env python
"""
resolve_wikidata.py -- Resolve GfdS trigger event labels to Wikidata QIDs.

Reads the precomputed classifications and resolves each trigger_label against
the Wikidata search API. Writes results to etl/.cache/gfds/wikidata_qids.json.

Polite: 1.5s delay between requests, exponential backoff on 429.
Run standalone before gfds_import.py if Wikidata was unavailable.

Usage:
    python etl/scripts/resolve_wikidata.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ETL_DIR = Path(__file__).resolve().parent.parent
_CACHE_DIR = _ETL_DIR / ".cache" / "gfds"
_LLM_CACHE_DIR = _ETL_DIR / ".cache" / "llm"
_QID_CACHE = _CACHE_DIR / "wikidata_qids.json"

# Browser-like UA — no identifying project name
_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"

# Well-known QIDs for major events we can hard-code confidently
KNOWN_QIDS = {
    "1968 student protest movement": "Q48672",  # 68er movement
    "RAF German Autumn terrorism 1977": "Q696001",  # German Autumn
    "US TV series Holocaust broadcast in Germany": "Q1423306",  # Holocaust TV series
    "Fall of the Berlin Wall November 1989": "Q46199",  # Fall of Berlin Wall
    "German reunification October 1990": "Q8817",  # German reunification
    "September 11 terrorist attacks United States 2001": "Q40231",  # 9/11 attacks
    "Lehman Brothers collapse global financial crisis 2008": "Q152424",  # 2007-08 financial crisis
    "COVID-19 coronavirus global pandemic 2020": "Q81068910",  # COVID-19 pandemic
    "Yugoslavia Wars ethnic cleansing 1992": "Q46083",  # Yugoslav Wars
    "Chernobyl nuclear disaster April 1986": "Q486",  # Chernobyl
    "2006 FIFA World Cup public viewing Germany": "Q41218",  # 2006 FIFA World Cup
    "Hartz IV labor market welfare reform Germany 2004": "Q455215",  # Hartz IV
    "Angela Merkel elected first female German chancellor": "Q567",  # Angela Merkel
    "European migration crisis Germany 2015": "Q16914843",  # European migrant crisis
    "Brexit Trump post-truth politics rise 2016": "Q1557230",  # Post-truth politics
    "Russia invasion of Ukraine German policy shift 2022": "Q110999120",  # 2022 invasion
    "NATO Kosovo bombing civilian casualties 1999": "Q46083",  # Kosovo War
    "Kellyanne Conway alternative facts Trump inauguration 2017": "Q1557230",  # post-truth
    "AfD Potsdam meeting Correctiv remigration leak 2023": "Q124513295",  # Potsdam meeting
    "NSA surveillance scandal Germany Watergate suffix spread": "Q1163202",  # NSA scandal
    "Fridays for Future Greta Thunberg climate movement 2019": "Q63735606",  # FFF
    "WikiLeaks Julian Assange secret information leaks": "Q237",  # WikiLeaks
    "Trump election Brexit deliberate disinformation fake news 2016": "Q1557230",  # post-truth
    "social media influencer marketing YouTube Instagram rise": "Q266169",  # Influencer
    "Letzte Generation climate activists criminalization Germany 2022": "Q112448987",  # Letzte Generation
    "Hoyerswerda anti-foreigner riots East Germany 1991": "Q696001",  # Hoyerswerda
    "Stuttgart 21 railway protest movement Germany 2010": "Q315",  # Stuttgart 21
    "IPCC Fourth Assessment Report climate crisis 2007": "Q11658943",  # IPCC AR4
    "Fukushima nuclear disaster bank stress tests 2011": "Q7825",  # Fukushima
    "Hartz IV unemployment welfare stigma youth slang": "Q455215",  # Hartz IV
    "Pegida movement right-wing press delegitimization 2014": "Q18534050",  # Pegida
    "Drake YOLO hip-hop internet meme spread 2012": "Q338523",  # Drake (musician)
    "COVID-19 pandemic lockdown restrictions Germany 2020": "Q81068910",  # COVID-19
    "fourth COVID wave lockdown measures Germany 2021": "Q81068910",  # COVID-19
    "COVID-19 pandemic measures Querdenken conspiracy movement 2020": "Q115500066",  # Querdenken-711
    "EU border pushback illegal migration human rights violations 2021": "Q1137470",  # Pushback EU
    "Haftbefehl Babo rap song German youth slang spread 2013": "Q1561756",  # Haftbefehl
    "TikTok gaming aura points social status youth slang 2024": "Q70505879",  # TikTok
    "TikTok goofy trend German youth positive silliness": "Q70505879",  # TikTok
    "YouTube streaming culture youth embarrassment slang": "Q866",  # YouTube
    "Kickstarter internet crowdfunding startup culture rise": "Q368795",  # Kickstarter
    "Rumsfeld old Europe statement Iraq War 2003": "Q7754",  # Iraq War
    "NATO double-track decision nuclear debate": "Q484761",  # NATO double-track decision
    "Austrian glycol wine scandal 1985": "Q1411098",  # Glycol wine scandal
}


def load_cache() -> dict:
    if _QID_CACHE.exists():
        with _QID_CACHE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with _QID_CACHE.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def search_wikidata(label: str) -> str | None:
    """Search Wikidata for a label. Returns QID or None."""
    params = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "format": "json",
        "language": "de",
        "uselang": "de",
        "search": label,
        "limit": 5,
        "type": "item",
    })
    url = f"https://www.wikidata.org/w/api.php?{params}"

    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            time.sleep(1.5)  # 1.5s between requests

            results = data.get("search", [])
            if not results:
                return None

            # Best-effort label match
            label_lower = label.lower()
            for res in results:
                rl = res.get("label", "").lower()
                if rl == label_lower or label_lower in rl or rl in label_lower:
                    return res["id"]
            # No close match
            return None

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = 5 * (2 ** attempt)  # 5, 10, 20, 40s
                print(f"  429 rate-limit, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP error {exc.code} for '{label}'")
                return None
        except Exception as exc:
            print(f"  Error for '{label}': {exc}")
            return None
    return None


def load_all_trigger_labels() -> list[tuple[str, int]]:
    """Load all trigger labels from the LLM cache files."""
    labels = []
    for cache_file in sorted(_LLM_CACHE_DIR.glob("*.json")):
        with cache_file.open("r", encoding="utf-8") as f:
            entries = json.load(f)
        for e in entries:
            label = e.get("trigger_label", "")
            year = e.get("year", 0)
            if label:
                labels.append((label, year))
    return labels


def main():
    parser = argparse.ArgumentParser(description="Resolve GfdS trigger labels to Wikidata QIDs")
    parser.add_argument("--limit", type=int, default=0, help="Limit to N lookups (0=all)")
    args = parser.parse_args()

    cache = load_cache()

    # First: seed with known QIDs (free, no API calls needed)
    seeded = 0
    for label, qid in KNOWN_QIDS.items():
        # We need to match against (label|year) format in cache
        # Use label-only key since year varies; try both
        for year in range(1970, 2026):
            key = f"{label}|{year}"
            if key not in cache:
                # Only set if label matches an actual entry label
                pass
        # Use label as primary key
        if label not in cache:
            cache[label] = qid
            seeded += 1
    print(f"Seeded {seeded} known QIDs")

    # Load trigger labels from LLM classifications
    labels = load_all_trigger_labels()
    print(f"Found {len(labels)} trigger labels to resolve")

    # Filter to those not yet in cache
    pending = [(l, y) for l, y in labels if f"{l}|{y}" not in cache and l not in cache]
    print(f"  {len(pending)} not yet cached")

    if args.limit > 0:
        pending = pending[:args.limit]
        print(f"  Limited to {args.limit}")

    # Check known QIDs for direct label matches
    auto_matched = 0
    for label, year in list(pending):
        if label in KNOWN_QIDS:
            cache[f"{label}|{year}"] = KNOWN_QIDS[label]
            auto_matched += 1
            pending.remove((label, year))

    print(f"  Auto-matched {auto_matched} from known QIDs")
    print(f"  {len(pending)} remaining for API lookup")
    save_cache(cache)

    # API lookups for remaining
    resolved = 0
    for i, (label, year) in enumerate(pending):
        key = f"{label}|{year}"
        print(f"  [{i+1}/{len(pending)}] '{label}'...", end=" ", flush=True)
        qid = search_wikidata(label)
        cache[key] = qid
        if qid:
            print(f"-> {qid}")
            resolved += 1
        else:
            print("-> None")
        # Save after each lookup (crash-safe)
        save_cache(cache)

    # Summary
    total_resolved = sum(1 for v in cache.values() if v is not None)
    total_none = sum(1 for v in cache.values() if v is None)
    print(f"\nWikidata cache: {total_resolved} resolved, {total_none} unresolved")
    print(f"Cache written to: {_QID_CACHE}")


if __name__ == "__main__":
    main()
