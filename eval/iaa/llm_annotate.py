#!/usr/bin/env python3
"""
llm_annotate.py — local-LLM reliability pilot for the causal-hypothesis IAA study.

Three INDEPENDENT local model families (via ollama) rate every item in
eval/iaa/items.json on the codebook's Q1 (plausible? yes/no) and Q2 (justified
evidence tier 1-5). Using three different families (qwen3, phi4, gemma3) rather
than one model in three framings gives genuinely independent annotators, is free
(local-first, the project's stated principle), and is more defensible for kappa.

The curator is annotator 1 (added by kappa.py from items.json). This is a
reliability PROBE, not ground truth (see docs/annotation-guidelines.md).

Disk cache (eval/iaa/.cache) makes the run resumable and re-runs free.

Usage:
  python eval/iaa/llm_annotate.py --estimate     # print plan, do nothing
  python eval/iaa/llm_annotate.py                # run (resumable), write annotations
  python eval/iaa/llm_annotate.py --limit 6      # smoke test on 6 items
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
ITEMS = ROOT / "eval" / "iaa" / "items.json"
OUT = ROOT / "eval" / "iaa" / "llm-annotations.json"
CACHE = ROOT / "eval" / "iaa" / ".cache"
OLLAMA = "http://localhost:11434/api/chat"
BATCH = 6

# Three independent annotators = three model families.
ANNOTATORS = ["qwen3:14b", "phi4:latest", "gemma3:27b"]

SYSTEM = (
    "You are a careful historical linguist rating causal hypotheses about word-meaning change. "
    "Judge each item fairly and independently on the evidence shown. "
    "Reject triggers that postdate the new sense, are generic ('general language change'), "
    "circular, or too vague to explain the specific shift."
)

TASK = """\
For each item decide:
Q1 (q1): does the proposed trigger plausibly explain this shift in meaning? "yes" or "no".
Q2 (q2): the strongest evidence tier justified by the sources shown, integer 1-5:
  1 Speculative, 2 FrequencyCorrelation, 3 ChangeSignalAlignment, 4 LexicographicNote, 5 ScholarlyAttestation.

Return ONLY a JSON array, one object per item, in the same order:
[{"hyp_id":"...","q1":"yes","q2":4}]
No prose, no markdown, just the JSON array."""


def item_brief(it: dict) -> dict:
    return {
        "hyp_id": it["hyp_id"], "word": it["word"], "language": it["language"],
        "sense_from": it["sense_from"], "sense_to": it["sense_to"],
        "drift_type": it["drift_type"], "trigger": it["trigger_label"],
        "trigger_date": it["trigger_date"], "trigger_desc": (it["trigger_desc"] or "")[:280],
        "sources": it["sources"],
    }


def cache_path(model: str, batch: list[dict]) -> pathlib.Path:
    h = hashlib.sha256((model + json.dumps(batch, sort_keys=True)).encode()).hexdigest()[:16]
    return CACHE / f"{model.replace(':', '_')}_{h}.json"


def ollama_chat(model: str, user: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM + "\n\n" + TASK},
                     {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]


def parse_array(text: str) -> list[dict]:
    t = text.strip()
    # strip <think>...</think> (qwen3) and code fences
    if "</think>" in t:
        t = t.split("</think>")[-1].strip()
    if "```" in t:
        import re
        m = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
        if m:
            t = m.group(1).strip()
    s, e = t.find("["), t.rfind("]")
    if s != -1 and e != -1:
        t = t[s:e + 1]
    return json.loads(t)


def run_model(model: str, items: list[dict]) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    ann: dict[str, dict] = {}
    for i in range(0, len(items), BATCH):
        batch = [item_brief(x) for x in items[i:i + BATCH]]
        cp = cache_path(model, batch)
        if cp.exists():
            rows = json.loads(cp.read_text())
        else:
            try:
                rows = parse_array(ollama_chat(model, json.dumps(batch, ensure_ascii=False)))
            except Exception as ex:
                print(f"    {model}: batch {i//BATCH+1} parse/api error: {ex}; marking null")
                rows = [{"hyp_id": b["hyp_id"], "q1": None, "q2": None} for b in batch]
            cp.write_text(json.dumps(rows, ensure_ascii=False))
        for r in rows:
            if isinstance(r, dict) and r.get("hyp_id"):
                q1 = str(r.get("q1", "")).lower().strip()
                ann[r["hyp_id"]] = {"q1": "yes" if q1.startswith("y") else ("no" if q1.startswith("n") else None),
                                    "q2": r.get("q2")}
        print(f"    {model}: batch {i//BATCH+1}/{(len(items)+BATCH-1)//BATCH}")
    return ann


def main() -> int:
    items = json.loads(ITEMS.read_text())
    if "--limit" in sys.argv:
        items = items[: int(sys.argv[sys.argv.index("--limit") + 1])]
    n_batches = (len(items) + BATCH - 1) // BATCH
    if "--estimate" in sys.argv:
        print(f"Items: {len(items)} | annotators: {ANNOTATORS} | batches/model: {n_batches} "
              f"| total local inferences: {n_batches*len(ANNOTATORS)} | cost: $0 (local)")
        return 0

    out = {"backend": "ollama", "annotators": {}, "n_items": len(items)}
    for model in ANNOTATORS:
        print(f"  Annotator: {model}")
        out["annotators"][model] = run_model(model, items)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(items)} items x {len(ANNOTATORS)} annotators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
