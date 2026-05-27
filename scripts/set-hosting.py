#!/usr/bin/env python3
"""Switch the Hosting section of site/datenschutz.html between deployment targets.

The page makes two kinds of privacy claims:

  * Page-content claims (no cookies, no tracking, no embedded third-party
    content). These are host-independent and live outside the managed block.
  * The *Hosting* claim, which depends on who serves the site:
      - github   : served by GitHub Pages (GitHub, Inc., USA) via Fastly CDN.
                   Visitor IPs are processed by GitHub -> must be disclosed,
                   incl. the US third-country transfer.
      - selfhost : served from own infrastructure -> first-party server logs.

The Hosting section is delimited in datenschutz.html by:
    <!-- HOSTING:BEGIN ... --> ... <!-- HOSTING:END -->
Only the content between those markers is rewritten; the markers stay so the
switch is idempotent and re-runnable.

Usage:
    python scripts/set-hosting.py --target github     # default; for xorwell.github.io
    python scripts/set-hosting.py --target selfhost   # for word-drift.xorwell.de
    python scripts/set-hosting.py --check             # print current target, exit 0/1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "site" / "datenschutz.html"

BEGIN = "<!-- HOSTING:BEGIN (managed by scripts/set-hosting.py --target github|selfhost) -->"
END = "<!-- HOSTING:END -->"

GITHUB = """
    <p class="section-label" style="margin-top: 2.5rem;">Art. 6 Abs. 1 lit. f DSGVO</p>
    <h2 class="section-title">Hosting</h2>
    <div class="section-body">
      <p>
        Diese Website wird über <strong>GitHub Pages</strong> bereitgestellt, einen Dienst
        der GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA
        (Tochterunternehmen der Microsoft Corporation). Die Auslieferung erfolgt über das
        Content-Delivery-Netzwerk von Fastly.
      </p>
      <p>
        Beim Aufruf der Seiten verarbeitet GitHub technisch notwendige Zugriffsdaten,
        insbesondere die <strong>IP-Adresse</strong> des anfragenden Geräts, um die Inhalte
        auszuliefern und den Betrieb sicher und stabil zu halten. GitHub speichert
        Zugriffsprotokolle zu Sicherheitszwecken. Auf diese serverseitige Protokollierung
        haben wir keinen Zugriff.
      </p>
      <p>
        Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO; das berechtigte Interesse liegt in
        der sicheren und kostengünstigen Bereitstellung der Website. Da GitHub, Inc. ihren
        Sitz in den USA hat, kann es zu einer Übermittlung personenbezogener Daten in ein
        Drittland kommen. GitHub stützt solche Übermittlungen auf die
        EU-Standardvertragsklauseln (Art. 46 DSGVO) bzw. das EU-US Data Privacy Framework.
      </p>
      <p>
        Weitere Informationen:
        <a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">GitHub Privacy Statement</a>.
      </p>
    </div>
"""

SELFHOST = """
    <p class="section-label" style="margin-top: 2.5rem;">Art. 6 Abs. 1 lit. f DSGVO</p>
    <h2 class="section-title">Hosting und Server-Logfiles</h2>
    <div class="section-body">
      <p>
        Diese Website wird auf eigener Infrastruktur (Server in Deutschland) betrieben.
        Beim Aufruf verarbeitet der Webserver automatisch Zugriffsdaten (Server-Logfiles):
      </p>
      <p>
        IP-Adresse, Datum und Uhrzeit des Zugriffs, die angeforderte URL, der verwendete
        Browser (User-Agent) sowie die zuvor besuchte Seite (Referrer).
      </p>
      <p>
        Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO. Unser berechtigtes Interesse liegt
        im sicheren und stabilen Betrieb der Website. Die Logfiles werden nur kurzfristig
        zu Sicherheits- und Betriebszwecken gespeichert und anschließend gelöscht.
      </p>
    </div>
"""

BLOCKS = {"github": GITHUB, "selfhost": SELFHOST}


def detect_target(inner: str) -> str | None:
    if "GitHub Pages" in inner:
        return "github"
    if "auf eigener Infrastruktur" in inner:
        return "selfhost"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=sorted(BLOCKS), default="github")
    ap.add_argument("--check", action="store_true", help="report current target and exit")
    args = ap.parse_args()

    html = PAGE.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    m = pattern.search(html)
    if not m:
        print(f"error: HOSTING markers not found in {PAGE}", file=sys.stderr)
        return 2

    if args.check:
        current = detect_target(m.group(0)) or "unknown"
        print(current)
        return 0

    replacement = f"{BEGIN}{BLOCKS[args.target]}    {END}"
    new_html = html[: m.start()] + replacement + html[m.end():]
    if new_html == html:
        print(f"datenschutz.html already set to target '{args.target}'")
        return 0
    PAGE.write_text(new_html, encoding="utf-8")
    print(f"datenschutz.html hosting section set to target '{args.target}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
