#!/usr/bin/env python3
"""Resolve GfdS word-of-the-year source URLs to specific dictionary entries.

For each drift:Source in data/gfds/*.ttl whose dct:title names a GfdS award
word, derive the lemma and resolve the best specific source URL:
  1. DWDS dictionary entry  https://www.dwds.de/wb/<lemma>
  2. Duden                  https://www.duden.de/rechtschreibung/<lemma>
  3. Wikipedia per-year anchor on the award page (if the anchor exists)
  4. generic award page (last resort)

A DWDS "no entry" page is detected by the title starting with "[Suche]".
This script only VERIFIES/RESOLVES and prints a mapping; it does not edit TTL.
Output: TSV  src_iri<TAB>lemma<TAB>tier<TAB>url  to stdout.
"""
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

GFDS = Path(__file__).resolve().parent.parent / "data" / "gfds"
UA = "Mozilla/5.0 (word-drift source-link verifier; reg@nennemann.de)"

AWARD_PAGE = {
    "anglizismus": "https://de.wikipedia.org/wiki/Anglizismus_des_Jahres",
    "jugendwort": "https://de.wikipedia.org/wiki/Jugendwort_des_Jahres_(Deutschland)",
    "unwort": "https://de.wikipedia.org/wiki/Unwort_des_Jahres_(Deutschland)",
    "wort": "https://de.wikipedia.org/wiki/Wort_des_Jahres_(Deutschland)",
}

_cache: dict[str, str] = {}


def fetch_title(url: str) -> str | None:
    if url in _cache:
        return _cache[url]
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                _cache[url] = ""
                return ""
            html = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        _cache[url] = ""
        sys.stderr.write(f"  ! fetch error {url}: {e}\n")
        return ""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = m.group(1).strip() if m else ""
    _cache[url] = title
    time.sleep(0.4)
    return title


def dwds_ok(lemma: str) -> str | None:
    url = "https://www.dwds.de/wb/" + urllib.parse.quote(lemma)
    title = fetch_title(url)
    if title and not title.startswith("[Suche]"):
        return url
    return None


def duden_ok(lemma: str) -> str | None:
    # Duden slugs: lowercase-ish, umlauts spelled out, spaces -> underscore.
    slug = (
        lemma.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
        .replace("ß", "sz").replace(" ", "_")
    )
    url = "https://www.duden.de/rechtschreibung/" + urllib.parse.quote(slug)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = r.status == 200
    except Exception:  # noqa: BLE001
        ok = False
    time.sleep(0.4)
    return url if ok else None


def wiki_anchor(award: str, year: str) -> str | None:
    page = AWARD_PAGE[award]
    title = fetch_title(page + f"#{year}")  # title same regardless of anchor
    # Determine anchor existence by scanning page html for id="<year>"
    req = urllib.request.Request(page, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    if f'id="{year}"' in html:
        return f"{page}#{year}"
    return None


TITLE_RE = re.compile(
    r'dct:title "GfdS / Wikipedia - (\w+) des Jahres (\d{4}): (.+?)"@en'
)
SRC_RE = re.compile(r"^(wdr:\S+) a drift:Source ;")


def main() -> None:
    for ttl in sorted(GFDS.glob("*.ttl")):
        award = ttl.stem
        lines = ttl.read_text(encoding="utf-8").splitlines()
        cur_src = None
        for line in lines:
            ms = SRC_RE.match(line)
            if ms:
                cur_src = ms.group(1)
                continue
            mt = TITLE_RE.search(line)
            if mt:
                year, lemma = mt.group(2), mt.group(3)
                tier, url = resolve(award, year, lemma)
                print(f"{cur_src}\t{lemma}\t{tier}\t{url}")
                sys.stderr.write(f"[{award} {year}] {lemma} -> {tier}\n")


def resolve(award: str, year: str, lemma: str) -> tuple[str, str]:
    u = dwds_ok(lemma)
    if u:
        return "dwds", u
    u = duden_ok(lemma)
    if u:
        return "duden", u
    u = wiki_anchor(award, year)
    if u:
        return "wiki-anchor", u
    return "generic", AWARD_PAGE[award]


if __name__ == "__main__":
    main()
