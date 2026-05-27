#!/usr/bin/env python3
"""Apply resolved GfdS source URLs to data/gfds/*.ttl.

Reads the TSV mapping (src_iri<TAB>lemma<TAB>tier<TAB>url) produced by
resolve-gfds-sources.py and rewrites ONLY the drift:sourceURL line that
belongs to each drift:Source node. Nothing else is touched.
"""
import re
import sys
from pathlib import Path

GFDS = Path(__file__).resolve().parent.parent / "data" / "gfds"
SRC_RE = re.compile(r"^(wdr:\S+) a drift:Source ;")
URL_RE = re.compile(r'^(\s*drift:sourceURL )"[^"]*"(\^\^xsd:anyURI\s*\.)\s*$')


def main(tsv_path: str) -> None:
    mapping: dict[str, str] = {}
    for line in Path(tsv_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        src, _lemma, _tier, url = line.split("\t")
        mapping[src] = url

    total = 0
    for ttl in sorted(GFDS.glob("*.ttl")):
        lines = ttl.read_text(encoding="utf-8").splitlines(keepends=True)
        out: list[str] = []
        cur_src = None
        changed = 0
        for line in lines:
            ms = SRC_RE.match(line)
            if ms:
                cur_src = ms.group(1)
                out.append(line)
                continue
            mu = URL_RE.match(line)
            if mu and cur_src and cur_src in mapping:
                nl = line[: line.index("\n")] if "\n" in line else line
                ending = "\n" if line.endswith("\n") else ""
                out.append(f'{mu.group(1)}"{mapping[cur_src]}"{mu.group(2).rstrip()}\n' if ending else
                           f'{mu.group(1)}"{mapping[cur_src]}"{mu.group(2)}')
                changed += 1
                cur_src = None
                continue
            out.append(line)
        ttl.write_text("".join(out), encoding="utf-8")
        print(f"{ttl.name}: {changed} sourceURL updated")
        total += changed
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/gfds-map.tsv")
