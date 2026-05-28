"""Word Drift 3.0 — multi-group metrics (M3).

Three load-bearing metrics, all computed from ``drift:MeaningAttribution``
records. Mathematically clean; deliberately no numpy dependency.

Conventions
-----------
- Every metric takes a Trails ``kg`` and a ``word`` written form.
- ``year`` is an optional snapshot year. When ``None``, the metric is
  computed over the full attribution history.
- Every metric returns a dict with at least a ``value`` field. When the
  metric is undefined for the input (e.g. <2 groups, <2 senses, no
  attributions, total weight under a minimum-evidence threshold), the
  function returns ``{"value": None, "reason": "..."}`` — never a
  meaningless zero. Per the metrics doc: "return null with a stated
  reason. There is no third option."

Math
----
- ``semantic_entropy``: Shannon entropy of the unconditioned sense
  distribution, in bits. Range [0, log2(|S|)] with |S| = #distinct senses.
- ``semantic_fragmentation_index``: 1 - Σ p(g,s)² over the joint
  (group, sense) distribution (Gini-Simpson diversity). Range [0, 1-1/n]
  with n = #(g,s) cells.
- ``group_divergence``: pairwise Jensen-Shannon divergence between the
  sense-distributions of two groups, in bits. Range [0, 1].
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

_MIN_EVIDENCE = 0.5  # Minimum total attribution weight before a metric is reportable.


# ---------------------------------------------------------------------------
# Shared SPARQL: load attribution rows for a word, optionally at a year.
# ---------------------------------------------------------------------------


def _attribution_rows(
    kg: Any, *, word: str, year: int | None = None,
) -> list[dict[str, Any]]:
    """Return rows: {senseIri, groupIri, platformIri, atYear, weight} for one word."""
    year_filter = f'FILTER(STR(?atYear) = "{int(year)}")' if year is not None else ""
    sparql = f"""
PREFIX drift: <https://w3id.org/word-drift/ontology#>

SELECT ?senseIri ?groupIri ?platformIri ?atYear ?weight
WHERE {{
  ?ma a drift:MeaningAttribution ;
      drift:attributesWord ?wordIri ;
      drift:attributesSense ?senseIri ;
      drift:byGroup ?groupIri .
  ?wordIri drift:writtenForm ?word .
  FILTER(STR(?word) = "{word}")
  OPTIONAL {{ ?ma drift:onPlatform ?platformIri . }}
  OPTIONAL {{ ?ma drift:atYear ?atYear . }}
  OPTIONAL {{ ?ma drift:attributionWeight ?weight . }}
  {year_filter}
}}
"""
    return kg.query(sparql)


def _weight(row: dict[str, Any]) -> float:
    """Extract attribution weight from a row, defaulting to 1.0."""
    w = row.get("weight")
    if w is None or w == "":
        return 1.0
    try:
        return float(w)
    except (TypeError, ValueError):
        return 1.0


# ---------------------------------------------------------------------------
# Metric 1 — semantic_entropy
# ---------------------------------------------------------------------------


def semantic_entropy(
    kg: Any, *, word: str = "Querdenker", year: int | None = None,
) -> dict[str, Any]:
    """Shannon entropy of the unconditioned sense distribution.

    Returns
    -------
    dict with keys:
        value:           entropy in bits, or None
        normalised:      entropy / log2(|S|) in [0, 1], or None
        n_senses:        number of distinct senses
        total_weight:    sum of attribution weights
        reason:          present only when value is None
    """
    rows = _attribution_rows(kg, word=word, year=year)

    sense_mass: dict[str, float] = defaultdict(float)
    total = 0.0
    for r in rows:
        s = r.get("senseIri")
        if not s:
            continue
        w = _weight(r)
        sense_mass[s] += w
        total += w

    n_senses = len(sense_mass)

    if total < _MIN_EVIDENCE:
        return {
            "value": None,
            "normalised": None,
            "n_senses": n_senses,
            "total_weight": total,
            "reason": "low_evidence",
        }
    if n_senses <= 1:
        return {
            "value": 0.0,
            "normalised": None,  # log2(1) = 0, division undefined
            "n_senses": n_senses,
            "total_weight": total,
            "reason": "monosemous_at_this_window" if n_senses == 1 else "no_attributions",
        }

    h = -sum((m / total) * math.log2(m / total) for m in sense_mass.values() if m > 0)
    return {
        "value": h,
        "normalised": h / math.log2(n_senses),
        "n_senses": n_senses,
        "total_weight": total,
    }


# ---------------------------------------------------------------------------
# Metric 2 — semantic_fragmentation_index
# ---------------------------------------------------------------------------


def semantic_fragmentation_index(
    kg: Any, *, word: str = "Querdenker", year: int | None = None,
) -> dict[str, Any]:
    """Gini-Simpson diversity over the joint (group, sense) distribution.

    Captures how spread-out the population of attributions is across the
    (group, sense) grid. A monosemous word held by one group scores 0; a
    word with several groups each backing several senses scores high.

    Returns
    -------
    dict with keys:
        value:        1 - Σ p(g,s)², or None
        n_cells:      number of distinct (group, sense) cells
        n_groups:     distinct groups
        n_senses:     distinct senses
        total_weight: sum of weights
    """
    rows = _attribution_rows(kg, word=word, year=year)

    cell_mass: dict[tuple[str, str], float] = defaultdict(float)
    groups: set[str] = set()
    senses: set[str] = set()
    total = 0.0
    for r in rows:
        s = r.get("senseIri")
        g = r.get("groupIri")
        if not s or not g:
            continue
        w = _weight(r)
        cell_mass[(g, s)] += w
        groups.add(g)
        senses.add(s)
        total += w

    n_cells = len(cell_mass)
    n_groups = len(groups)
    n_senses = len(senses)

    if total < _MIN_EVIDENCE:
        return {
            "value": None,
            "n_cells": n_cells,
            "n_groups": n_groups,
            "n_senses": n_senses,
            "total_weight": total,
            "reason": "low_evidence",
        }
    if n_cells <= 1:
        return {
            "value": 0.0,
            "n_cells": n_cells,
            "n_groups": n_groups,
            "n_senses": n_senses,
            "total_weight": total,
        }

    sumsq = sum((m / total) ** 2 for m in cell_mass.values())
    return {
        "value": 1.0 - sumsq,
        "n_cells": n_cells,
        "n_groups": n_groups,
        "n_senses": n_senses,
        "total_weight": total,
    }


# ---------------------------------------------------------------------------
# Metric 3 — group_divergence (pairwise JSD)
# ---------------------------------------------------------------------------


def _jsd(p: dict[str, float], q: dict[str, float]) -> float:
    """Jensen-Shannon divergence in bits between distributions p, q.

    Both p and q are normalised; missing keys are treated as 0. Returns
    a value in [0, 1] when both distributions are real (Shannon log base 2
    bounds JSD by 1).
    """
    keys = set(p) | set(q)
    m = {k: 0.5 * p.get(k, 0.0) + 0.5 * q.get(k, 0.0) for k in keys}

    def kl(a: dict[str, float], b: dict[str, float]) -> float:
        total = 0.0
        for k, ak in a.items():
            if ak <= 0.0:
                continue
            bk = b.get(k, 0.0)
            if bk <= 0.0:
                continue
            total += ak * math.log2(ak / bk)
        return total

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def _group_distribution(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Per-group sense distribution, normalised."""
    raw: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        g = r.get("groupIri")
        s = r.get("senseIri")
        if not g or not s:
            continue
        raw[g][s] += _weight(r)

    out: dict[str, dict[str, float]] = {}
    for g, sense_to_mass in raw.items():
        total = sum(sense_to_mass.values())
        if total <= 0:
            continue
        out[g] = {s: m / total for s, m in sense_to_mass.items()}
    return out


def group_divergence(
    kg: Any,
    *,
    word: str = "Querdenker",
    year: int | None = None,
) -> dict[str, Any]:
    """Pairwise Jensen-Shannon divergence between group sense-distributions.

    Returns
    -------
    dict with keys:
        pairs:        [{groupA, groupB, jsd}] for every unordered pair
        max:          max JSD across pairs, or None
        mean:         mean JSD across pairs, or None
        n_groups:     distinct groups
        total_weight: sum of weights
        reason:       present when max/mean are None
    """
    rows = _attribution_rows(kg, word=word, year=year)
    dist = _group_distribution(rows)
    total = sum(_weight(r) for r in rows if r.get("senseIri") and r.get("groupIri"))

    n_groups = len(dist)
    if n_groups < 2:
        return {
            "pairs": [],
            "max": None,
            "mean": None,
            "n_groups": n_groups,
            "total_weight": total,
            "reason": "need_at_least_two_groups",
        }
    if total < _MIN_EVIDENCE:
        return {
            "pairs": [],
            "max": None,
            "mean": None,
            "n_groups": n_groups,
            "total_weight": total,
            "reason": "low_evidence",
        }

    group_iris = sorted(dist.keys())
    pairs: list[dict[str, Any]] = []
    jsds: list[float] = []
    for i, ga in enumerate(group_iris):
        for gb in group_iris[i + 1:]:
            j = _jsd(dist[ga], dist[gb])
            pairs.append({"groupA": ga, "groupB": gb, "jsd": j})
            jsds.append(j)

    return {
        "pairs": pairs,
        "max": max(jsds),
        "mean": sum(jsds) / len(jsds),
        "n_groups": n_groups,
        "total_weight": total,
    }


# ---------------------------------------------------------------------------
# Metric 4 — cross_platform_distance (M6)
# Reuses the JSD machinery but conditions distributions on platform.
# ---------------------------------------------------------------------------


def _platform_distribution(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    raw: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        p = r.get("platformIri")
        s = r.get("senseIri")
        if not p or not s:
            continue
        raw[p][s] += _weight(r)
    out: dict[str, dict[str, float]] = {}
    for p, sense_to_mass in raw.items():
        total = sum(sense_to_mass.values())
        if total <= 0:
            continue
        out[p] = {s: m / total for s, m in sense_to_mass.items()}
    return out


def cross_platform_distance(
    kg: Any,
    *,
    word: str = "Querdenker",
    year: int | None = None,
) -> dict[str, Any]:
    """Pairwise JSD between platform sense-distributions for a word.

    Same shape as group_divergence but axis = platform. Captures whether
    the same word is read the same way across Reddit, Twitter, mainstream
    press, parliamentary protocols. A value near zero means platforms agree
    on the sense distribution; near 1 means platform-native readings.

    Returns
    -------
    dict with keys:
        pairs:        [{platformA, platformB, jsd}]
        max:          max JSD
        mean:         mean JSD
        n_platforms:  distinct platforms
        total_weight: sum of weights on platform-tagged attributions
        reason:       present when max/mean are None
    """
    rows = _attribution_rows(kg, word=word, year=year)
    dist = _platform_distribution(rows)
    total = sum(_weight(r) for r in rows if r.get("platformIri") and r.get("senseIri"))

    n = len(dist)
    if n < 2:
        return {
            "pairs": [],
            "max": None,
            "mean": None,
            "n_platforms": n,
            "total_weight": total,
            "reason": "need_at_least_two_platforms",
        }
    if total < _MIN_EVIDENCE:
        return {
            "pairs": [],
            "max": None,
            "mean": None,
            "n_platforms": n,
            "total_weight": total,
            "reason": "low_evidence",
        }

    plats = sorted(dist.keys())
    pairs: list[dict[str, Any]] = []
    jsds: list[float] = []
    for i, pa in enumerate(plats):
        for pb in plats[i + 1:]:
            j = _jsd(dist[pa], dist[pb])
            pairs.append({"platformA": pa, "platformB": pb, "jsd": j})
            jsds.append(j)

    return {
        "pairs": pairs,
        "max": max(jsds),
        "mean": sum(jsds) / len(jsds),
        "n_platforms": n,
        "total_weight": total,
    }


# ---------------------------------------------------------------------------
# Metric 5 — emotional_drift (M7)
# Group-conditioned valence trajectory: (weighted) mean valence per group
# per year, plus a delta between adjacent years that measures emotional
# drift independent of denotational drift.
# ---------------------------------------------------------------------------


def emotional_drift(
    kg: Any,
    *,
    word: str = "Querdenker",
) -> dict[str, Any]:
    """Per-group, per-year (weighted) mean valence for a word.

    Returns
    -------
    dict with keys:
        timeline:  list of {year, group, valence_mean, loading_mean, n_framings}
        deltas:    list of {group, fromYear, toYear, delta} — valence drift
                   for each group between adjacent years.
        n_groups:  distinct groups with framing data
        total_framings: total number of framing records observed
    """
    sparql = f"""
PREFIX drift: <https://w3id.org/word-drift/ontology#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?groupIri ?groupLabel ?atYear ?valence ?loading ?weight
WHERE {{
  ?fr a drift:EmotionalFraming ;
      drift:framesAttribution ?ma ;
      drift:valence ?valence .
  OPTIONAL {{ ?fr drift:loading ?loading . }}
  ?ma drift:attributesWord ?wordIri ;
      drift:byGroup ?groupIri .
  ?wordIri drift:writtenForm ?word .
  FILTER(STR(?word) = "{word}")
  OPTIONAL {{
    ?groupIri rdfs:label ?groupLabel .
    FILTER(LANG(?groupLabel) = "en" || LANG(?groupLabel) = "")
  }}
  OPTIONAL {{ ?ma drift:atYear ?atYear . }}
  OPTIONAL {{ ?ma drift:attributionWeight ?weight . }}
}}
"""
    rows = kg.query(sparql)

    # Aggregate per (group, year): weighted-mean valence + mean loading.
    # Weight = attribution weight × framing loading (default 1 each).
    by_cell: dict[tuple[str, int], dict[str, float]] = {}
    group_labels: dict[str, str] = {}
    for r in rows:
        g_id = r.get("groupIri")
        y_raw = r.get("atYear")
        try:
            year = int(str(y_raw)[:4]) if y_raw else None
        except (TypeError, ValueError):
            year = None
        if not g_id or year is None:
            continue
        try:
            val = float(r.get("valence")) if r.get("valence") not in (None, "") else None
        except (TypeError, ValueError):
            val = None
        if val is None:
            continue
        try:
            load = float(r.get("loading")) if r.get("loading") not in (None, "") else 1.0
        except (TypeError, ValueError):
            load = 1.0
        try:
            aw = float(r.get("weight")) if r.get("weight") not in (None, "") else 1.0
        except (TypeError, ValueError):
            aw = 1.0
        w = aw * load
        cell = by_cell.setdefault((g_id, year), {
            "val_sum": 0.0, "w_sum": 0.0, "load_sum": 0.0, "n": 0.0,
        })
        cell["val_sum"] += val * w
        cell["w_sum"] += w
        cell["load_sum"] += load
        cell["n"] += 1
        group_labels.setdefault(g_id, str(r.get("groupLabel") or g_id))

    timeline: list[dict[str, Any]] = []
    for (g_id, year), c in sorted(by_cell.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if c["w_sum"] <= 0:
            continue
        timeline.append({
            "year": year,
            "group": g_id,
            "groupLabel": group_labels.get(g_id, g_id),
            "valence_mean": c["val_sum"] / c["w_sum"],
            "loading_mean": c["load_sum"] / c["n"] if c["n"] else 0.0,
            "n_framings": int(c["n"]),
        })

    # Deltas per group between adjacent attested years.
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in timeline:
        by_group[row["group"]].append(row)
    deltas: list[dict[str, Any]] = []
    for g, rows_for_g in by_group.items():
        rows_for_g.sort(key=lambda r: r["year"])
        for prev, curr in zip(rows_for_g, rows_for_g[1:]):
            deltas.append({
                "group": g,
                "groupLabel": prev["groupLabel"],
                "fromYear": prev["year"],
                "toYear": curr["year"],
                "delta": curr["valence_mean"] - prev["valence_mean"],
            })

    return {
        "timeline": timeline,
        "deltas": deltas,
        "n_groups": len(by_group),
        "total_framings": sum(int(r["n_framings"]) for r in timeline),
    }


# ---------------------------------------------------------------------------
# Convenience wrapper: timeline of all three metrics per year.
# ---------------------------------------------------------------------------


def metric_timeline(
    kg: Any, *, word: str = "Querdenker",
) -> list[dict[str, Any]]:
    """Per-year snapshot of the three M3 metrics for ``word``.

    Returns
    -------
    list of dicts ordered by year, each with keys:
        year, entropy, fragmentation, divergence_max, divergence_mean,
        n_groups, n_senses, total_weight
    """
    # Discover the years for which this word has attributions.
    rows = _attribution_rows(kg, word=word, year=None)
    years = sorted({int(str(r["atYear"])[:4]) for r in rows if r.get("atYear")})

    out: list[dict[str, Any]] = []
    for y in years:
        ent = semantic_entropy(kg, word=word, year=y)
        frag = semantic_fragmentation_index(kg, word=word, year=y)
        div = group_divergence(kg, word=word, year=y)
        plat = cross_platform_distance(kg, word=word, year=y)
        out.append({
            "year": y,
            "entropy": ent.get("value"),
            "entropy_normalised": ent.get("normalised"),
            "fragmentation": frag.get("value"),
            "divergence_max": div.get("max"),
            "divergence_mean": div.get("mean"),
            "platform_divergence_max": plat.get("max"),
            "platform_divergence_mean": plat.get("mean"),
            "n_groups": div.get("n_groups", 0),
            "n_platforms": plat.get("n_platforms", 0),
            "n_senses": ent.get("n_senses", 0),
            "total_weight": ent.get("total_weight", 0.0),
        })
    return out
