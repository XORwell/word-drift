"""
histwords_de.py -- HistWords German diachronic embeddings, cosine-drift scorer.

Downloads Hamilton et al. decade-binned SGNS vectors for German from:
  http://snap.stanford.edu/historical_embeddings/ger/

Each decade file is ~60MB. The script downloads only the two endpoint decades
(1960s and 2010s) to compute the cosine drift between them -- the most
informative pair for our 1960-2019 window. If the download is too slow or
exceeds a size budget, it falls back gracefully and produces no scores.

Usage (standalone):
  python -u etl/histwords_de.py [--output-scores path/to/scores.json] [--budget-mb N]

Called automatically by freq_pipeline.py if this file exists.

Output:
  --output-scores (default: data/freq/_histwords_scores.json)
  JSON mapping word_lower -> cosine_drift (float, 0.0 to 2.0).
  A score of 0.0 means identical usage across decades; 2.0 means fully opposed.
  Typical significant-shift threshold: >= 0.3.

HARD RULES:
  - NO LLM.
  - Does NOT touch etl/_llm.py, examples/, ontology/, shapes/, site/.
  - Only writes to data/freq/ and etl/.cache/.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np

# Ensure etl/ is on path for _common import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import slugify

ROOT       = Path(__file__).resolve().parent.parent
CACHE_DIR  = Path(__file__).resolve().parent / ".cache" / "histwords"
OUTPUT_DIR = ROOT / "data" / "freq"

# HistWords German base URL (Hamilton et al. 2016)
# The German SGNS vectors are in a single bundled file (all decades together):
#   https://snap.stanford.edu/historical_embeddings/ger-all_sgns.zip  (~400MB)
# This exceeds our default 200MB budget, so we skip the download by default.
# Raise --budget-mb to attempt a download. The ZIP contains decade sub-files
# named e.g. "1960/ger-all_sgns.txt" or similar -- we use the earliest and latest.
HW_BASE    = "https://snap.stanford.edu/historical_embeddings/"
HW_BUNDLE  = "ger-all_sgns.zip"
HW_UA      = "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
HW_DECADES = ["1960s", "2000s"]   # early vs late (using 2000s as proxy for "later")

MAX_BUDGET_MB = 200    # skip download if the bundle exceeds this (default: skip)


def _download_bundle(budget_mb: int) -> Optional[Path]:
    """
    Download the ger-all_sgns.zip bundle into the cache.
    Returns the local path, or None if skipped/failed.

    NOTE: The file is ~400MB. By default (budget_mb=200) this is skipped.
    Pass --budget-mb 500 or higher to attempt a download.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_zip = CACHE_DIR / HW_BUNDLE

    if local_zip.exists():
        print(f"  [histwords] {HW_BUNDLE} already cached at {local_zip}")
        return local_zip

    url = f"{HW_BASE}{HW_BUNDLE}"
    headers = {"User-Agent": HW_UA}

    # HEAD check for size
    try:
        head_req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(head_req, timeout=15) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > budget_mb:
                    print(f"  [histwords] {HW_BUNDLE} is {size_mb:.0f}MB > budget {budget_mb}MB; SKIPPING.")
                    print(f"  [histwords] Re-run with --budget-mb {int(size_mb)+50} to download.")
                    return None
                print(f"  [histwords] downloading {HW_BUNDLE} ({size_mb:.0f}MB)...")
            else:
                print(f"  [histwords] downloading {HW_BUNDLE} (size unknown)...")
    except Exception as e:
        print(f"  [histwords] HEAD failed for {HW_BUNDLE}: {e}; skipping")
        return None

    req = urllib.request.Request(url, headers=headers)
    try:
        tmp_path = local_zip.with_suffix(".tmp")
        with urllib.request.urlopen(req, timeout=600) as resp:
            chunk_size = 1024 * 1024  # 1 MB chunks
            downloaded = 0
            with open(tmp_path, "wb") as fh:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (20 * chunk_size) == 0:
                        print(f"  [histwords] {HW_BUNDLE}: {downloaded // (1024*1024)}MB downloaded...")
        tmp_path.rename(local_zip)
        print(f"  [histwords] {HW_BUNDLE}: download complete ({local_zip.stat().st_size // (1024*1024)}MB)")
        return local_zip
    except Exception as e:
        print(f"  [histwords] download failed for {HW_BUNDLE}: {e}")
        tmp_path = local_zip.with_suffix(".tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        return None


def _parse_vectors_from_zip(zip_path: Path, target_decade: Optional[str] = None) -> dict[str, np.ndarray]:
    """
    Parse word2vec text format from a zip archive.
    Returns {word: vector_array}.
    """
    import zipfile

    vectors: dict[str, np.ndarray] = {}
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # Filter by target decade if specified
            txt_files = [n for n in names if n.endswith(".txt") or n.endswith(".bin")]
            if target_decade:
                decade_prefix = target_decade.rstrip("s")  # "1960s" -> "1960"
                decade_files = [n for n in txt_files if decade_prefix in n]
                if decade_files:
                    txt_files = decade_files
                else:
                    print(f"  [histwords] no decade-{target_decade} file found; available: {names[:10]}")
                    return vectors
            if not txt_files:
                print(f"  [histwords] no .txt/.bin in {zip_path.name}: {names[:5]}")
                return vectors
            fname = txt_files[0]
            print(f"  [histwords] parsing {fname} from {zip_path.name}...")
            with zf.open(fname) as fh:
                # First line is "vocab_size dim"
                header = fh.readline().decode("utf-8", errors="ignore").strip()
                try:
                    _vocab_size, dim = map(int, header.split())
                except ValueError:
                    print(f"  [histwords] unexpected header: {header!r}; skipping")
                    return vectors
                for line in fh:
                    parts = line.decode("utf-8", errors="ignore").rstrip().split(" ")
                    if len(parts) < dim + 1:
                        continue
                    word = parts[0].lower()
                    try:
                        vec = np.array(parts[1:dim+1], dtype=np.float32)
                        vectors[word] = vec
                    except ValueError:
                        pass
        print(f"  [histwords] parsed {len(vectors)} vectors from {zip_path.name}")
    except Exception as e:
        print(f"  [histwords] parse error for {zip_path}: {e}")
    return vectors


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def compute_drift_scores(
    vectors_early: dict[str, np.ndarray],
    vectors_late: dict[str, np.ndarray],
) -> dict[str, float]:
    """
    Compute cosine drift for all words present in both vector sets.
    drift = 1 - cosine_similarity(early_vec, late_vec).
    Higher = more drift.
    """
    scores: dict[str, float] = {}
    common = set(vectors_early.keys()) & set(vectors_late.keys())
    print(f"  [histwords] {len(common)} words in both decades")
    for word in common:
        sim = cosine_similarity(vectors_early[word], vectors_late[word])
        scores[word] = round(1.0 - sim, 6)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="HistWords DE cosine-drift scorer")
    parser.add_argument("--output-scores", type=str,
                        default=str(OUTPUT_DIR / "_histwords_scores.json"),
                        help="Output JSON path for drift scores.")
    parser.add_argument("--budget-mb", type=int, default=MAX_BUDGET_MB,
                        help=f"Max MB per decade file to download. Default: {MAX_BUDGET_MB}.")
    args = parser.parse_args()

    output_path = Path(args.output_scores)
    if output_path.exists():
        print(f"[histwords] scores already at {output_path}, nothing to do")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[histwords] bundle: {HW_BUNDLE} (~400MB)  budget={args.budget_mb}MB")
    bundle_path = _download_bundle(args.budget_mb)

    if bundle_path is None:
        print("[histwords] bundle unavailable (budget exceeded or download failed).")
        print("[histwords] DECISION: skipping HistWords embeddings; writing empty scores.")
        print("[histwords] freq_pipeline.py will run on frequency change-points only.")
        output_path.write_text(json.dumps({}))
        return

    # The bundle contains per-decade sub-files; extract vectors for earliest and latest decade.
    vectors_early = _parse_vectors_from_zip(bundle_path, target_decade=HW_DECADES[0])
    vectors_late  = _parse_vectors_from_zip(bundle_path, target_decade=HW_DECADES[1])

    if not vectors_early or not vectors_late:
        print("[histwords] could not parse vectors; writing empty scores")
        output_path.write_text(json.dumps({}))
        return

    scores = compute_drift_scores(vectors_early, vectors_late)
    output_path.write_text(json.dumps(scores, ensure_ascii=False))
    print(f"[histwords] wrote {len(scores)} drift scores to {output_path}")

    # Print top-20 drifters
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
    print("[histwords] top-20 drifters:")
    for w, s in top:
        print(f"  {w:<30} cosine_drift={s:.4f}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    main()
