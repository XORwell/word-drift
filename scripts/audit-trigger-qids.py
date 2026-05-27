#!/usr/bin/env python3
"""
audit-trigger-qids.py — audit every owl:sameAs link from a drift:TriggerEvent
to a Wikidata Q-item, and classify each as OK / BAD / SUSPECT.

Motivation
----------
A wrong Wikidata link (e.g. trigger-aws-launch -> Q7117978 = a Wikimedia
"Category:" page) makes the explorer's "About this event" card show garbage.
The QIDs in data/wikidata/trigger-links.ttl + inline in examples/ were matched
heuristically and never hand-verified. This script verifies each one against
the live Wikidata entity and flags links that can never be a real referent.

Classification
--------------
* BAD (auto-removable): the entity is a Wikimedia category (P31 Q4167836),
  disambiguation page (Q4167410), Wikimedia list article (Q13406463),
  template / help / project / module / portal page, OR its label literally
  starts with "Category:" / "List of" / "Template:" / "Wikipedia:" etc.
  Such an entity can never be the real-world referent of a trigger event.
* SUSPECT (flag for human, do NOT remove): the entity *kind* (from P31) seems
  mismatched to the trigger's drift:triggerCategory, or the entity label has
  weak token overlap with the trigger label. A human decides.
* OK: plausible (person for an eponym, event for an event, org / work / place
  as appropriate).

Outputs
-------
* data/reports/wikidata-audit.md — full table + SUSPECT list + counts.
* (when run with --apply) removes BAD owl:sameAs triples from
  data/wikidata/trigger-links.ttl and surgically from inline examples/*.ttl.

Re-runnable & polite
--------------------
* All HTTP cached under .cache/wikidata-audit/ (keyed by URL hash).
* 0.5 s delay between *uncached* requests; descriptive User-Agent.

Cost: $0 (Wikidata is free; no LLM).

Usage
-----
    python scripts/audit-trigger-qids.py            # audit + write report (dry, no edits)
    python scripts/audit-trigger-qids.py --apply     # also remove BAD links in place
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
CACHE_DIR = ROOT / ".cache" / "wikidata-audit"
LINKS_TTL = ROOT / "data" / "wikidata" / "trigger-links.ttl"
REPORT_MD = ROOT / "data" / "reports" / "wikidata-audit.md"

DRIFT = "https://w3id.org/word-drift/ontology#"
OWL = "http://www.w3.org/2002/07/owl#"
WD_ENTITY = "http://www.wikidata.org/entity/"

USER_AGENT = "word-drift-research/0.4 (https://w3id.org/word-drift; research@nennemann.de)"
REQUEST_DELAY_S = 0.5

# --- P31 classes that mark an entity that can NEVER be a real-world referent.
NON_REFERENT_P31 = {
    "Q4167836": "Wikimedia category",
    "Q4167410": "Wikimedia disambiguation page",
    "Q13406463": "Wikimedia list article",
    "Q11266439": "Wikimedia template",
    "Q4663903": "Wikimedia portal",
    "Q15184295": "Wikimedia module",
    "Q14204246": "Wikimedia project page",
    "Q11753321": "Wikimedia navigational template",
    "Q35252665": "Wikimedia non-content page",
    "Q17442446": "Wikimedia internal item",
    "Q22808320": "Wikimedia human name disambiguation page",
    "Q21528878": "Wikimedia set category",
    "Q24046192": "Wikimedia category of stubs",
    "Q20010800": "Wikimedia user language category",
    "Q15407973": "Wikimedia disambiguation category",
    "Q56428020": "Wikimedia category redirect",
    "Q59542487": "Wikimedia draft article",
}

# QIDs confirmed wrong by earlier audits (must never re-enter as OK).
KNOWN_WRONG_QIDS = {
    "Q7117978": "Category:People from Burbank, California (was on aws-launch)",
    "Q97203077": "deleted/empty item (was on querdenken-711; correct is Q115500066)",
    "Q189962": "interval, a frequency ratio (was on funk; correct is Q164444)",
    "Q47545": "Norwegian Sea / junk coord (was on german-reunification; correct Q56039)",
    "Q1110398": "Croisy-sur-Andelle commune (was on WWW; correct is Q466)",
    "Q12494": "wrong Chernobyl id (correct is Q486)",
}

# label prefixes that prove a non-referent regardless of P31
BAD_LABEL_PREFIXES = (
    "category:",
    "list of ",
    "liste der ",
    "liste von ",
    "template:",
    "vorlage:",
    "wikipedia:",
    "wikimedia:",
    "help:",
    "hilfe:",
    "module:",
    "portal:",
    "draft:",
    "module talk:",
)

# --- P31 -> broad kind, for the SUSPECT mismatch heuristic.
PERSON_P31 = {"Q5"}
EVENT_P31 = {
    "Q1190554", "Q1656682", "Q1914636", "Q198", "Q178561", "Q1261499",
    "Q830494", "Q3839081", "Q175331", "Q49773", "Q49780", "Q208701",
    "Q2738074", "Q124734", "Q12909644", "Q98391050", "Q4688003",
    "Q645883", "Q1827102", "Q831663", "Q45382", "Q657449", "Q15631336",
    "Q135976384", "Q14547231", "Q16510064", "Q44512", "Q12198",
    "Q3241045", "Q1006311", "Q18608583", "Q41397", "Q2401485",
    "Q15275719", "Q189760", "Q3024240",  # recurring / historical / volunteer event etc.
}
ORG_P31 = {
    "Q43229", "Q4830453", "Q783794", "Q891723", "Q4438121", "Q48204",
    "Q49773", "Q2659904", "Q1365916", "Q1530022", "Q163740", "Q31855",
    "Q327333", "Q7278", "Q875538", "Q4671277",  # nonprofit/govt/party/univ etc.
}
WORK_P31 = {
    "Q571", "Q7725634", "Q47461344", "Q25379", "Q116476516", "Q1667921",
    "Q8261", "Q386724", "Q838948", "Q49084", "Q149537", "Q1318295",
    "Q105543609", "Q7889", "Q11424", "Q482994", "Q134556", "Q2188189",
    "Q5398426", "Q1107656",  # video game / film / album / single / series etc.
}
PRODUCT_P31 = {
    "Q11019", "Q1183543", "Q42889", "Q39546", "Q15401930", "Q2424752",
    "Q205663", "Q169336", "Q11173", "Q12140", "Q1357761", "Q19603939",
    "Q8142", "Q79529", "Q317623", "Q40050",  # currency / chemical substance / std / drink
}
PLACE_P31 = {
    "Q486972", "Q515", "Q3957", "Q15273785", "Q493522", "Q4946461",
    "Q82794", "Q1620908", "Q62049", "Q148837", "Q15661340", "Q839954",
    "Q1549591", "Q1093829", "Q751708", "Q55237813", "Q23397", "Q42523",
    "Q5119", "Q6256", "Q3624078", "Q35657", "Q123705",  # country / sovereign / state / neighborhood
}


def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def http_get_json(url: str) -> dict:
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


def fetch_entity(qid: str) -> dict:
    """Return {label, description, p31:[(qid,label)...], _error}."""
    url = (
        "https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&format=json&ids={qid}&props=labels|descriptions|claims&languages=en|de"
    )
    try:
        data = http_get_json(url)
    except Exception as e:
        return {"label": "", "description": "", "p31": [], "_error": str(e)}
    ent = data.get("entities", {}).get(qid, {})
    if "missing" in ent:
        return {"label": "", "description": "", "p31": [], "_error": "missing entity"}
    labels = ent.get("labels", {})
    label = (labels.get("en") or labels.get("de") or {}).get("value", "")
    descs = ent.get("descriptions", {})
    desc = (descs.get("en") or descs.get("de") or {}).get("value", "")
    p31: list[str] = []
    for st in ent.get("claims", {}).get("P31", []):
        dv = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(dv, dict) and "id" in dv:
            p31.append(dv["id"])
    return {"label": label, "description": desc, "p31": p31, "_error": None}


# --------------------------------------------------------------------------- #
# collect links from the graph
# --------------------------------------------------------------------------- #
def collect_links() -> list[dict]:
    """Return list of {triggerId, label, category, qid, file} for every
    drift:TriggerEvent owl:sameAs wd:Q... triple, with the file the sameAs
    triple lives in (examples/* or data/wikidata/trigger-links.ttl)."""
    import rdflib

    # 1. one merged graph to learn each trigger's rdfs:label + triggerCategory
    g = rdflib.Graph()
    files: list[Path] = []
    for pat in ["examples/**/*.ttl", "data/**/*.ttl"]:
        files += [Path(p) for p in glob.glob(str(ROOT / pat), recursive=True)]
    files = sorted(set(files))
    for f in files:
        # skip non-trigger trig/nanopub noise but include all ttl
        try:
            g.parse(str(f), format="turtle")
        except Exception as e:
            print(f"  warn: parse {f}: {e}", file=sys.stderr)

    drift = rdflib.Namespace(DRIFT)
    owl = rdflib.Namespace(OWL)
    RDFS = rdflib.RDFS

    # Map each trigger -> the word(s) it is about, via
    # hypothesis(proposedTrigger=T, aboutDrift=D) -> D affectsWord W -> writtenForm.
    trigger_words: dict[str, set[str]] = {}
    for hyp in g.subjects(drift.proposedTrigger, None):
        for t in g.objects(hyp, drift.proposedTrigger):
            forms: set[str] = set()
            for d in g.objects(hyp, drift.aboutDrift):
                for w in g.objects(d, drift.affectsWord):
                    for wf in g.objects(w, drift.writtenForm):
                        forms.add(str(wf))
                    lbl = g.value(w, RDFS.label)
                    if lbl:
                        forms.add(str(lbl))
            trigger_words.setdefault(str(t), set()).update(forms)

    trigger_meta: dict[str, dict] = {}
    for s in g.subjects(rdflib.RDF.type, drift.TriggerEvent):
        sid = str(s)
        label = g.value(s, RDFS.label)
        cat = g.value(s, drift.triggerCategory)
        desc = g.value(s, rdflib.URIRef("http://purl.org/dc/terms/description"))
        trigger_meta[sid] = {
            "label": str(label) if label else "",
            "category": str(cat).split("#")[-1] if cat else "",
            "desc": str(desc) if desc else "",
            "words": sorted(trigger_words.get(sid, set())),
        }

    # 2. which file(s) does each sameAs triple physically live in?  The same
    #    trigger IRI + QID can appear in several files (e.g. an en/de word pair
    #    sharing one trigger), so track ALL files per (subject, qid).
    link_files: dict[tuple[str, str], list[str]] = {}
    for f in files:
        fg = rdflib.Graph()
        try:
            fg.parse(str(f), format="turtle")
        except Exception:
            continue
        for s, o in fg.subject_objects(owl.sameAs):
            so, oo = str(s), str(o)
            if oo.startswith(WD_ENTITY) and re.fullmatch(r"Q\d+", oo[len(WD_ENTITY):]):
                # only count subjects that are trigger events somewhere in the graph
                if so in trigger_meta:
                    rel = str(f.relative_to(ROOT))
                    link_files.setdefault((so, oo), [])
                    if rel not in link_files[(so, oo)]:
                        link_files[(so, oo)].append(rel)

    links = []
    for (sid, obj), fpaths in sorted(link_files.items()):
        qid = obj[len(WD_ENTITY):]
        meta = trigger_meta.get(sid, {})
        links.append({
            "triggerId": sid.split("/")[-1],
            "triggerIri": sid,
            "label": meta.get("label", ""),
            "category": meta.get("category", ""),
            "desc": meta.get("desc", ""),
            "words": meta.get("words", []),
            "qid": qid,
            "files": fpaths,
            "file": ", ".join(fpaths),
        })
    return links


# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #
STOP = {
    "the", "of", "a", "an", "and", "or", "de", "der", "die", "das", "von",
    "and", "in", "at", "to", "by", "his", "her", "its", "for", "as", "s",
    "founds", "launches", "patents", "markets", "devises", "introduces",
    "publishes", "first", "early", "movement", "campaign", "battle", "war",
    "tests", "test", "school", "brand", "play", "system", "trade", "use",
    "1818", "1595", "1831", "popularisation", "popularization", "emergence",
    "rise", "launch", "invention", "discovery",
}


def _fold(text: str) -> str:
    """Lowercase + strip diacritics (ä->a, ö->o, é->e, ß->ss) for fuzzy match."""
    import unicodedata
    t = text.lower().replace("ß", "ss")
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def tokens(text: str) -> set[str]:
    t = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in t.split() if len(w) > 2 and w not in STOP and not w.isdigit()}


CATEGORY_TO_KINDS = {
    # drift:triggerCategory -> acceptable broad kinds
    "Technology": {"product", "org", "event", "person", "work", "place"},
    "Cultural": {"event", "work", "person", "org", "place", "product"},
    "Political": {"event", "org", "person", "place"},
    "Scientific": {"person", "event", "product", "work", "org"},
    "Economic": {"org", "event", "person", "place", "product"},
    "Social": {"event", "org", "person", "movement", "place"},
    "Military": {"event", "person", "org", "place"},
    "Religious": {"event", "org", "person", "place", "work"},
    "Linguistic": {"person", "work", "event", "place", "org", "product"},
}


def kinds_for_p31(p31: list[str]) -> set[str]:
    out = set()
    for q in p31:
        if q in PERSON_P31:
            out.add("person")
        if q in EVENT_P31:
            out.add("event")
        if q in ORG_P31:
            out.add("org")
        if q in WORK_P31:
            out.add("work")
        if q in PRODUCT_P31:
            out.add("product")
        if q in PLACE_P31:
            out.add("place")
    return out


def classify(link: dict, ent: dict) -> dict:
    """Return {verdict, kind, reason}. verdict in OK/BAD/SUSPECT."""
    # Denylist: QIDs confirmed wrong by past audits. They must never re-enter as
    # OK regardless of the per-trigger token heuristic (which once rated the wrong
    # funk link Q189962 OK on one trigger and SUSPECT on another).
    if link["qid"] in KNOWN_WRONG_QIDS:
        return {"verdict": "BAD", "kind": "denylisted",
                "reason": f"known-wrong QID ({KNOWN_WRONG_QIDS[link['qid']]})"}

    if ent.get("_error"):
        return {"verdict": "SUSPECT", "kind": "?",
                "reason": f"could not verify ({ent['_error']})"}

    label = ent["label"]
    desc = ent["description"]
    p31 = ent["p31"]
    llow = label.lower()

    # BAD: label prefix
    for pre in BAD_LABEL_PREFIXES:
        if llow.startswith(pre):
            return {"verdict": "BAD", "kind": "non-referent",
                    "reason": f'label starts with "{label[:24]}"'}

    # BAD: P31 is a non-referent class
    for q in p31:
        if q in NON_REFERENT_P31:
            return {"verdict": "BAD", "kind": "non-referent",
                    "reason": f"P31 {q} = {NON_REFERENT_P31[q]}"}
    # also catch by description wording for safety
    dlow = desc.lower()
    if dlow.startswith(("wikimedia category", "wikipedia category",
                        "wikimedia disambiguation", "wikipedia disambiguation",
                        "wikimedia list", "topic page", "wikimedia template")):
        return {"verdict": "BAD", "kind": "non-referent",
                "reason": f'description: "{desc[:40]}"'}

    # determine broad kind
    kinds = kinds_for_p31(p31)
    kind_str = "/".join(sorted(kinds)) if kinds else "other"

    # --- evidence of a real connection between trigger and entity ----------
    # Build the trigger's "context" (label + description + the word lemma(s)
    # whose drift this trigger explains) and the entity's text (label + desc).
    # A correct eponym link (word 'ampere' -> André-Marie *Ampère*) or event
    # link (trigger 'Battle of Leyte Gulf' described in the desc) will share a
    # distinctive token even when the trigger's rdfs:label is a verb phrase.
    ctx_tokens = tokens(link["label"]) | tokens(link.get("desc", ""))
    word_tokens: set[str] = set()
    for w in link.get("words", []):
        word_tokens |= tokens(w)
    ent_text = label + " " + desc
    ent_tokens = tokens(ent_text)
    ent_fold = _fold(ent_text)

    overlap = (ctx_tokens | word_tokens) & ent_tokens
    # substring / diacritic-folded match (e.g. word 'ampere' inside 'ampère',
    # 'roentgen' inside 'röntgen', 'boykott' inside 'boycott')
    fuzzy = False
    for tok in (ctx_tokens | word_tokens):
        if len(tok) >= 4 and _fold(tok) in ent_fold:
            fuzzy = True
            break

    connected = bool(overlap) or fuzzy

    # mismatch: we know the entity kind, and it's disallowed for the category
    cat = link["category"]
    allowed = CATEGORY_TO_KINDS.get(cat, set())
    kind_mismatch = bool(kinds and allowed and not (kinds & allowed))

    if connected and not kind_mismatch:
        return {"verdict": "OK", "kind": kind_str, "reason": ""}

    # No textual connection (and/or kind mismatch) -> a human must look.
    if not label and not desc:
        why = "entity has no en/de label or description (deleted/empty item?)"
    elif kind_mismatch and not connected:
        why = (f"entity is a {kind_str} ('{label}') with no textual overlap; "
               f"unexpected for {cat or 'uncat'} trigger")
    elif kind_mismatch:
        why = f"kind {kind_str} ('{label}') unexpected for {cat or 'uncat'} trigger"
    else:
        why = f"no textual overlap between trigger and entity '{label}'"
    return {"verdict": "SUSPECT", "kind": kind_str, "reason": why}


# --------------------------------------------------------------------------- #
# applying removals
# --------------------------------------------------------------------------- #
def remove_from_links_ttl(bad_pairs: set[tuple[str, str]]) -> int:
    """Remove `wdr:<id> owl:sameAs wd:<qid> .` lines from trigger-links.ttl."""
    if not LINKS_TTL.exists():
        return 0
    lines = LINKS_TTL.read_text(encoding="utf-8").splitlines(keepends=True)
    out, removed = [], 0
    skip_prev_comment = False
    for ln in lines:
        m = re.match(r"\s*wdr:(\S+)\s+owl:sameAs\s+wd:(Q\d+)\s*\.\s*$", ln)
        if m and (m.group(1), m.group(2)) in bad_pairs:
            removed += 1
            # also drop a trailing blank line that may follow; and the comment
            # immediately above (the "# ... matched ..." line) if present.
            if out and out[-1].lstrip().startswith("#"):
                out.pop()
            skip_prev_comment = True
            continue
        out.append(ln)
    if removed:
        LINKS_TTL.write_text("".join(out), encoding="utf-8")
    return removed


def remove_inline(file_rel: str, trigger_id: str, qid: str) -> bool:
    """Surgically remove the `owl:sameAs wd:Qxxx` line from an example file,
    fixing the preceding `;` to `.` so the Turtle stays valid. Only touches
    the sameAs line of the given trigger."""
    fpath = ROOT / file_rel
    lines = fpath.read_text(encoding="utf-8").splitlines(keepends=True)

    # find the sameAs line for this trigger+qid
    target = None
    for i, ln in enumerate(lines):
        if re.search(rf"owl:sameAs\s+wd:{qid}\b", ln):
            # verify it belongs to trigger_id: scan upward to the subject decl
            for j in range(i, -1, -1):
                ms = re.match(r"\s*(wdr:\S+|<[^>]+>)\s+a\s+", lines[j])
                if ms:
                    subj = ms.group(1)
                    if subj.endswith(trigger_id) or trigger_id in subj:
                        target = i
                    break
            if target is not None:
                break
    if target is None:
        return False

    sameas_line = lines[target]
    is_last = sameas_line.rstrip().endswith(".")
    # remove the sameAs line
    del lines[target]
    if is_last:
        # the property before it ended with ';' -> change that ';' to '.'
        for k in range(target - 1, -1, -1):
            stripped = lines[k].rstrip("\n")
            if stripped.rstrip().endswith(";"):
                lines[k] = stripped.rstrip()[:-1].rstrip() + " .\n"
                break
            if stripped.strip() == "" or stripped.lstrip().startswith("#"):
                continue
            # property already ends with '.' (shouldn't happen) -> stop
            break
    else:
        # sameAs ended with ';' (not last) -> nothing else to fix; the next
        # property keeps the statement valid.
        pass
    fpath.write_text("".join(lines), encoding="utf-8")
    return True


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="remove BAD owl:sameAs links in place")
    ap.add_argument("--strict", action="store_true",
                    help="remove BAD *and* SUSPECT links (keep only verified-OK)")
    ap.add_argument("--check", action="store_true",
                    help="gate: exit 1 if any trigger owl:sameAs is not verified-OK")
    args = ap.parse_args()

    print("Collecting trigger -> Wikidata owl:sameAs links ...", file=sys.stderr)
    links = collect_links()
    print(f"  {len(links)} links across "
          f"{len({l['file'] for l in links})} files; "
          f"{len({l['qid'] for l in links})} distinct QIDs", file=sys.stderr)

    # fetch each distinct QID once
    qid_ent: dict[str, dict] = {}
    distinct = sorted({l["qid"] for l in links}, key=lambda q: int(q[1:]))
    for n, qid in enumerate(distinct, 1):
        if qid not in qid_ent:
            qid_ent[qid] = fetch_entity(qid)
        print(f"  [{n}/{len(distinct)}] {qid} -> "
              f"{qid_ent[qid].get('label') or qid_ent[qid].get('_error')}",
              file=sys.stderr)

    rows = []
    for l in links:
        ent = qid_ent[l["qid"]]
        c = classify(l, ent)
        rows.append({**l, **c,
                     "entLabel": ent.get("label", ""),
                     "entDesc": ent.get("description", ""),
                     "p31": ent.get("p31", [])})

    bad = [r for r in rows if r["verdict"] == "BAD"]
    suspect = [r for r in rows if r["verdict"] == "SUSPECT"]
    ok = [r for r in rows if r["verdict"] == "OK"]

    # --check gate: any link that is not verified-OK fails (for make release / CI).
    if args.check:
        not_ok = bad + suspect
        if not_ok:
            print(f"TRIGGER-QID CHECK FAILED: {len(not_ok)} link(s) not verified-OK "
                  f"({len(bad)} BAD, {len(suspect)} SUSPECT). Run --strict to remove, "
                  f"or hand-verify + correct.", file=sys.stderr)
            for r in not_ok[:20]:
                print(f"  - {r['triggerId']} -> {r['qid']} "
                      f"({r.get('entLabel') or r.get('reason')})", file=sys.stderr)
            return 1
        print(f"trigger-qid check: all {len(ok)} links verified-OK.", file=sys.stderr)
        return 0

    # --- apply removals. A trigger+QID may physically appear in several files
    # (e.g. an en/de word pair sharing one trigger); remove from each.
    # --apply removes BAD; --strict removes BAD and SUSPECT (keep only OK).
    to_remove = bad + (suspect if args.strict else [])
    if (args.apply or args.strict) and to_remove:
        ttl_pairs = {(r["triggerId"], r["qid"]) for r in to_remove
                     if any(f.endswith("trigger-links.ttl") for f in r["files"])}
        n_ttl = remove_from_links_ttl(ttl_pairs)
        n_inline = 0
        for r in to_remove:
            for f in r["files"]:
                if f.endswith("trigger-links.ttl"):
                    continue
                if remove_inline(f, r["triggerId"], r["qid"]):
                    n_inline += 1
        print(f"  removed {n_ttl} from trigger-links.ttl, "
              f"{n_inline} inline triple(s) "
              f"({'strict: BAD+SUSPECT' if args.strict else 'BAD only'})",
              file=sys.stderr)

    write_report(rows, bad, suspect, ok, applied=(args.apply or args.strict))
    print(f"\nReport written: {REPORT_MD.relative_to(ROOT)}", file=sys.stderr)
    print(f"OK={len(ok)}  BAD={len(bad)}  SUSPECT={len(suspect)}  "
          f"total={len(rows)}", file=sys.stderr)
    return 0


def write_report(rows, bad, suspect, ok, applied: bool):
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    L = []
    L.append("# Wikidata trigger-link audit\n")
    L.append("Audit of every `owl:sameAs` link from a `drift:TriggerEvent` to a "
             "Wikidata Q-item. Each QID was verified against the live entity "
             "(`wbgetentities`, P31 instance-of) and classified.\n")
    L.append(f"- **Total links audited:** {len(rows)} "
             f"({len({r['qid'] for r in rows})} distinct QIDs)")
    L.append(f"- **OK:** {len(ok)}")
    L.append(f"- **BAD (removed):** {len(bad)}"
             + ("" if applied else " (dry run, not yet removed)"))
    L.append(f"- **SUSPECT (flagged for human review):** {len(suspect)}\n")

    if suspect:
        L.append("## SUSPECT: human review needed\n")
        L.append("These links were **left in place**. A human should decide "
                 "whether to keep, fix, or remove each.\n")
        L.append("| Trigger | Trigger label | Cat | QID | Entity label | Entity description | Why flagged |")
        L.append("|---|---|---|---|---|---|---|")
        for r in sorted(suspect, key=lambda x: x["triggerId"]):
            L.append(f"| `{r['triggerId']}` | {esc(r['label'])} | {r['category']} "
                     f"| [{r['qid']}](https://www.wikidata.org/wiki/{r['qid']}) "
                     f"| {esc(r['entLabel'])} | {esc(r['entDesc'])} | {esc(r['reason'])} |")
        L.append("")

    if bad:
        L.append("## BAD: removed (non-referent: category / disambig / list / template)\n")
        L.append("| Trigger | QID | Was actually | Lived in |")
        L.append("|---|---|---|---|")
        for r in sorted(bad, key=lambda x: x["triggerId"]):
            actual = r["entLabel"] or "(no label)"
            if r["entDesc"]:
                actual += f" ({r['entDesc']})"
            L.append(f"| `{r['triggerId']}` "
                     f"| [{r['qid']}](https://www.wikidata.org/wiki/{r['qid']}) "
                     f"| {esc(actual)} ({esc(r['reason'])}) | `{r['file']}` |")
        L.append("")

    L.append("## Full audit table\n")
    L.append("| Trigger | Cat | QID | Entity label | P31 | Verdict |")
    L.append("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x["verdict"], x["triggerId"])):
        p31s = ", ".join(r["p31"][:3]) or "-"
        L.append(f"| `{r['triggerId']}` | {r['category']} "
                 f"| [{r['qid']}](https://www.wikidata.org/wiki/{r['qid']}) "
                 f"| {esc(r['entLabel'])} | {p31s} | {r['verdict']} |")
    L.append("")
    REPORT_MD.write_text("\n".join(L), encoding="utf-8")


def esc(s: str) -> str:
    # also fold em-/en-dashes from verbatim Wikidata strings to a hyphen so the
    # report obeys the project's no-em-dash convention.
    return ((s or "").replace("|", "\\|").replace("\n", " ")
            .replace("—", "-").replace("–", "-"))


if __name__ == "__main__":
    sys.exit(main())
