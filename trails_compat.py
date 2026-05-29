"""Trails framework compatibility declaration + runtime check.

word-drift is built against a specific range of the Trails framework.
The range is declared here once; the check runs at app bootstrap and is
exposed by the ``/api/version`` endpoint so a Trails-side breakage
surfaces fast and obvious in production logs.

Bump ``TRAILS_REQUIRED_RANGE`` when adopting new Trails features or when
a backward-incompatible change in Trails forces a port. Bump
``TRAILS_TESTED_AGAINST`` after every Trails revision that the
word-drift test suite (62 tests + the M5/M6/M7/M8 examples) was actually
run against — that is the version we know works end-to-end.

The Trails-side surface used by word-drift today (routed through
``trails.sdk`` per ADR-0082):
- ``trails.sdk.capability``, ``trails.sdk.Context``
- ``trails.sdk.node_type``, ``trails.sdk.shape``, ``trails.sdk.predicate``,
  ``trails.sdk.Model``
- ``trails.sdk.kernel_store``, ``trails.sdk.raw_kernel_store``
- ``trails.sdk.KG`` query / update / bind-param API
- ``trails.sdk.MCPServer``
- ``trails.sdk.HTTPAdapter``
- ``trails.sdk.validate_query`` (indirectly via ``trails.sdk.sparql``)

Any change to that surface in a future Trails release MUST be reflected
in the range here; word-drift should never silently consume a breaking
upstream change.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("word_drift.trails_compat")


# Range word-drift requires (PEP 440). Pre-release inclusive — Trails is
# alpha; we explicitly opt in to the alpha series and pin away from 0.2+
# until we have done a compatibility port.
TRAILS_REQUIRED_RANGE = ">=0.1.0a0, <0.2.0"

# The Trails version word-drift's CI / local pytest run was actually
# executed against. Reported alongside the live version so operators can
# tell whether they are on a tested combo or just an in-range one.
TRAILS_TESTED_AGAINST = "0.1.0a0"

# When the production environment flag is set and the installed Trails is
# OUTSIDE ``TRAILS_REQUIRED_RANGE``, the app refuses to start instead of
# logging-and-continuing. Override with WD_TRAILS_FAIL_OPEN=1 to relax
# the check in emergencies (a noisy WARNING is still logged).
TRAILS_PROD_ENV_VARS = ("TRAILS_ENV", "WD_ENV")
TRAILS_PROD_VALUES = {"production", "prod", "stable"}


@dataclass(frozen=True)
class TrailsCompat:
    """Outcome of the runtime Trails version check.

    Always returned in a single shape so observability code does not have
    to special-case import failures.
    """

    required: str
    tested_against: str
    installed: str
    satisfied: bool
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "tested_against": self.tested_against,
            "installed": self.installed,
            "satisfied": self.satisfied,
            "note": self.note,
        }


def check_trails() -> TrailsCompat:
    """Inspect the live Trails version and return a compat report.

    Never raises — even when Trails cannot be imported, returns a
    structured ``TrailsCompat`` with ``satisfied=False`` and a note
    explaining why.
    """
    try:
        import trails  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 — surface the cause in the note
        return TrailsCompat(
            required=TRAILS_REQUIRED_RANGE,
            tested_against=TRAILS_TESTED_AGAINST,
            installed=f"<import failed: {exc.__class__.__name__}>",
            satisfied=False,
            note=str(exc)[:200],
        )

    installed = str(getattr(trails, "__version__", "unknown"))
    ok, note = _satisfies(installed, TRAILS_REQUIRED_RANGE)
    return TrailsCompat(
        required=TRAILS_REQUIRED_RANGE,
        tested_against=TRAILS_TESTED_AGAINST,
        installed=installed,
        satisfied=ok,
        note=note,
    )


def enforce(compat: TrailsCompat | None = None) -> TrailsCompat:
    """Run the check and apply the production fail-fast policy.

    In a non-production environment a mismatch logs at WARNING and the
    app continues — convenient for development against a sibling Trails
    checkout that drifts ahead of the declared range. In production it
    raises ``RuntimeError`` unless ``WD_TRAILS_FAIL_OPEN=1`` is set.
    """
    compat = compat or check_trails()
    if compat.satisfied:
        logger.info(
            "trails compat OK: installed=%s required=%s tested=%s",
            compat.installed, compat.required, compat.tested_against,
        )
        return compat

    msg = (
        f"trails compat MISMATCH: installed={compat.installed!r} "
        f"required={compat.required!r} tested={compat.tested_against!r} "
        f"note={compat.note!r}"
    )
    is_prod = any(
        (os.environ.get(var) or "").strip().lower() in TRAILS_PROD_VALUES
        for var in TRAILS_PROD_ENV_VARS
    )
    fail_open = (os.environ.get("WD_TRAILS_FAIL_OPEN") or "").strip().lower() in {"1", "true", "yes"}

    if is_prod and not fail_open:
        logger.critical(msg)
        raise RuntimeError(msg)

    logger.warning(msg + " (continuing because not in production / FAIL_OPEN set)")
    return compat


def _satisfies(version: str, spec: str) -> tuple[bool, str]:
    """Check whether ``version`` is inside ``spec`` (PEP 440).

    Prefers ``packaging`` (installed transitively via pip) but falls back
    to a minimal comma-separated comparator parser when packaging is not
    importable. The fallback handles ``>=``, ``<``, ``<=``, ``>``, ``==``,
    and ``!=`` only.
    """
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import InvalidVersion, Version
    except Exception:
        return _satisfies_fallback(version, spec)

    try:
        v = Version(version)
    except InvalidVersion:
        return False, f"could not parse installed version {version!r}"
    try:
        s = SpecifierSet(spec)
    except Exception as exc:  # noqa: BLE001
        return False, f"could not parse spec {spec!r}: {exc}"
    return (v in s, f"checked {version} against {spec}")


def _satisfies_fallback(version: str, spec: str) -> tuple[bool, str]:
    """Tiny comparator used only when ``packaging`` is unavailable."""
    import re
    clauses = [c.strip() for c in spec.split(",") if c.strip()]
    v_tup = _parse_version_tuple(version)
    if v_tup is None:
        return False, f"could not parse installed version {version!r}"

    for clause in clauses:
        m = re.match(r"(>=|<=|==|!=|>|<)\s*([\w.\-+]+)", clause)
        if not m:
            return False, f"unsupported clause in fallback: {clause}"
        op, target = m.group(1), m.group(2)
        t_tup = _parse_version_tuple(target)
        if t_tup is None:
            return False, f"could not parse target {target!r}"
        cmp = (v_tup > t_tup) - (v_tup < t_tup)
        ok = {
            ">=": cmp >= 0, "<=": cmp <= 0,
            ">":  cmp > 0,  "<":  cmp < 0,
            "==": cmp == 0, "!=": cmp != 0,
        }[op]
        if not ok:
            return False, f"failed clause {clause} (cmp={cmp})"
    return True, f"checked {version} against {spec} (fallback)"


def _parse_version_tuple(v: str) -> tuple | None:
    """Coarse semver-with-pre tuple: (major, minor, patch, pre_kind, pre_n).

    Pre-release ordering: a < b < rc < <none>. Used only by the fallback
    comparator; production code should rely on ``packaging``.
    """
    import re
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?(?:\.dev\d+)?$", v)
    if not m:
        return None
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_kind = {"a": 0, "b": 1, "rc": 2, None: 3}[m.group(4)]
    pre_n = int(m.group(5)) if m.group(5) else 0
    return (major, minor, patch, pre_kind, pre_n)
