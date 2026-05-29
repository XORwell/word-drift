"""W12 — Real-data ingest pipeline tests.

Covers:
* DWUG DE/EN ingest emits valid Turtle (parses cleanly with rdflib).
* DWUG output contains >= 5 distinct words.
* All ingest outputs use deduplicated IRIs (no accidental duplicates).
* Cemetery threshold default is now 0.05 (was 0.30).
* The Querdenker fixture references at least one DWUG-derived source via
  prov:wasDerivedFrom.

Network sketches (Wikipedia / Bundestag / HN) are tested for *structure*
only — their content is rebuilt from live APIs by the ingest scripts and
is not checked in for stability tests. We require that whatever files are
present parse cleanly and obey the dedup rule.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA = _REPO_ROOT / "data"
_EXAMPLES = _REPO_ROOT / "examples"

# Files we expect to exist after a W12 ingest. The DWUG outputs are the
# load-bearing pair; the network sketches are best-effort and may be
# regenerated. We test them when present.
_DWUG_FILES = [
    _DATA / "dwug-de.ttl",
    _DATA / "dwug-en.ttl",
]
_OPTIONAL_FILES = [
    _DATA / "wiki-revisions-querdenker.ttl",
    _DATA / "bundestag-sample.ttl",
    _DATA / "hn-sample.ttl",
    _DATA / "reddit-sample.ttl",
]


def _parse(path: Path):
    import rdflib

    g = rdflib.Graph()
    g.parse(str(path), format="turtle")
    return g


# --- DWUG load-bearing tests ----------------------------------------------


def test_dwug_de_ttl_parses():
    path = _DATA / "dwug-de.ttl"
    if not path.exists():
        pytest.skip(f"missing {path} — run `python etl/dwug_ingest.py --lang de` first")
    g = _parse(path)
    assert len(g) > 0


def test_dwug_en_ttl_parses():
    path = _DATA / "dwug-en.ttl"
    if not path.exists():
        pytest.skip(f"missing {path} — run `python etl/dwug_ingest.py --lang en` first")
    g = _parse(path)
    assert len(g) > 0


def test_dwug_de_contains_at_least_5_distinct_words():
    path = _DATA / "dwug-de.ttl"
    if not path.exists():
        pytest.skip(f"missing {path}")
    g = _parse(path)
    sparql = """
    PREFIX drift: <https://w3id.org/word-drift/ontology#>
    SELECT DISTINCT ?w WHERE { ?w a drift:Word . }
    """
    rows = list(g.query(sparql))
    assert len(rows) >= 5, f"expected >=5 distinct DE words; got {len(rows)}"


def test_dwug_en_contains_at_least_5_distinct_words():
    path = _DATA / "dwug-en.ttl"
    if not path.exists():
        pytest.skip(f"missing {path}")
    g = _parse(path)
    sparql = """
    PREFIX drift: <https://w3id.org/word-drift/ontology#>
    SELECT DISTINCT ?w WHERE { ?w a drift:Word . }
    """
    rows = list(g.query(sparql))
    assert len(rows) >= 5, f"expected >=5 distinct EN words; got {len(rows)}"


def test_dwug_emits_meaning_attributions():
    path = _DATA / "dwug-de.ttl"
    if not path.exists():
        pytest.skip(f"missing {path}")
    g = _parse(path)
    sparql = """
    PREFIX drift: <https://w3id.org/word-drift/ontology#>
    SELECT (COUNT(?ma) AS ?n)
    WHERE { ?ma a drift:MeaningAttribution . }
    """
    rows = list(g.query(sparql))
    n = int(rows[0][0])
    # At least 5 words × ~20 attribs each minimum.
    assert n >= 100, f"expected many MeaningAttributions, got {n}"


# --- IRI dedup --------------------------------------------------------------


_SUBJECT_RE = re.compile(r"^(?:<[^>]+>|[A-Za-z][A-Za-z0-9_\-]*:[A-Za-z0-9_\-]+)\s")


def _toplevel_subjects(path: Path) -> list[str]:
    """Collect lines that introduce a new RDF subject (rough syntactic scan).

    We only flag the *toplevel* subject lines (column 0). Continuation
    triples on existing subjects start with whitespace and are skipped.
    This is a cheap dedup-check; rdflib itself would silently dedup so we
    have to look at the source text.
    """
    subjects: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(" ") or line.startswith("\t") or line.startswith("#"):
            continue
        if line.startswith("@"):
            continue
        m = _SUBJECT_RE.match(line)
        if m:
            subjects.append(m.group(0).strip())
    return subjects


@pytest.mark.parametrize("path", _DWUG_FILES + _OPTIONAL_FILES)
def test_no_duplicate_toplevel_subjects(path):
    if not path.exists():
        pytest.skip(f"optional file not present: {path}")
    subjects = _toplevel_subjects(path)
    counts = Counter(subjects)
    dups = {k: v for k, v in counts.items() if v > 1}
    assert not dups, f"duplicate toplevel subjects in {path.name}: {dups}"


# --- Optional sketches: parse-only ----------------------------------------


@pytest.mark.parametrize("path", _OPTIONAL_FILES)
def test_optional_sketch_parses_if_present(path):
    if not path.exists():
        pytest.skip(f"optional file not present: {path}")
    g = _parse(path)
    assert len(g) > 0


# --- Cemetery threshold ----------------------------------------------------


def test_cemetery_threshold_default_is_005():
    import inspect

    from capabilities.competency import cq15_semantic_cemetery

    sig = inspect.signature(cq15_semantic_cemetery)
    assert sig.parameters["threshold"].default == 0.05


# --- Querdenker fixture corpus-derived -------------------------------------


def test_querdenker_fixture_references_dwug_source():
    fixture = _EXAMPLES / "querdenker-multigroup.ttl"
    assert fixture.exists(), "querdenker-multigroup.ttl missing"
    text = fixture.read_text(encoding="utf-8")
    assert "prov:wasDerivedFrom" in text, (
        "the new corpus-derived Querdenker fixture must use prov:wasDerivedFrom"
    )
    assert "dwug-de-dynamik" in text or "dwug-de" in text, (
        "expected at least one wdr:attrib-dwug-de-… reference in the new fixture"
    )


def test_curated_querdenker_fixture_preserved():
    curated = _EXAMPLES / "querdenker-multigroup-curated.ttl"
    assert curated.exists(), (
        "expected examples/querdenker-multigroup-curated.ttl to hold the original "
        "curated fixture (renamed in W12)."
    )
    g = _parse(curated)
    assert len(g) > 0
