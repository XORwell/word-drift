"""Real-time SPARQL query trace for the word-drift Trails app.

Enabled when the env var ``WD_SPARQL_TRACE`` is truthy. When enabled, every
``kg.query()`` and ``kg.update()`` call writes one JSON-lines record to a
log file (default ``/tmp/word-drift-sparql.jsonl``) capturing:

    timestamp, kind (query|update), sparql_kind, duration_ms, row_count,
    trace_id, principal, sparql

Tail it with::

    tail -f /tmp/word-drift-sparql.jsonl | jq .

The wrapper is a small monkey-patch of :class:`trails.sdk.KG` because
Trails' built-in observability ``kg_query`` event deliberately does not
emit the SPARQL text. We add the text on top of the existing metadata so
both signals land together.

The wrapper is best-effort: any failure inside the logger never propagates
back into the calling query path. The original return value is always
preserved.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("word_drift.sparql_trace")
_install_lock = threading.Lock()
_installed = False


def _truthy(v: str | None) -> bool:
    return bool(v) and v.strip().lower() not in {"0", "false", "no", "off", ""}


def _log_path() -> Path:
    return Path(os.environ.get("WD_SPARQL_TRACE_FILE", "/tmp/word-drift-sparql.jsonl"))


def _max_bytes() -> int:
    """Trace-file rotation threshold (default 50 MB).

    Set via ``WD_SPARQL_TRACE_MAX_BYTES``. Below 1 KB the file would
    rotate after every line and is treated as disabled (returns a very
    large value).
    """
    try:
        n = int(os.environ.get("WD_SPARQL_TRACE_MAX_BYTES", str(50 * 1024 * 1024)))
    except ValueError:
        n = 50 * 1024 * 1024
    return n if n >= 1024 else (1 << 62)


_rotate_lock = threading.Lock()


def _maybe_rotate(path: Path) -> None:
    """Single-depth rotation: if the file exceeds the threshold, move it
    to ``<path>.1`` (replacing any existing ``.1``). No compression. The
    next write will recreate the primary file with 0600 perms.

    Best-effort: any failure here is logged but never propagates back to
    the caller.
    """
    try:
        st = path.stat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if st.st_size < _max_bytes():
        return
    with _rotate_lock:
        # Re-check under the lock; another thread may have rotated.
        try:
            if path.stat().st_size < _max_bytes():
                return
        except FileNotFoundError:
            return
        rotated = path.with_suffix(path.suffix + ".1")
        try:
            if rotated.exists():
                rotated.unlink()
            path.rename(rotated)
            logger.info("sparql trace rotated: %s -> %s", path, rotated)
        except OSError as exc:
            logger.warning("sparql trace rotation failed: %s", exc)


def _write_record(rec: dict[str, Any]) -> None:
    """Append a JSON-lines record to the trace file with 0600 permissions.

    The trace file captures SPARQL bodies and may contain user-supplied
    parameter values, so it must NOT be world-readable on shared hosts.
    We open with os.open(O_CREAT|O_APPEND, 0o600) on first write so the
    file is created with restrictive permissions even when umask is lax.
    Subsequent writes os.open the same fd path; if a prior process
    created the file with looser perms we re-chmod it back to 0o600.
    """
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Single-depth rotation before each write: bounded disk usage on
        # busy hosts. See _maybe_rotate() — best-effort, never fatal.
        _maybe_rotate(path)
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(str(path), flags, 0o600)
        try:
            # If the file already existed with looser perms, tighten them.
            try:
                st = os.fstat(fd)
                if (st.st_mode & 0o777) != 0o600:
                    os.fchmod(fd, 0o600)
            except (PermissionError, OSError):  # noqa: BLE001 — non-fatal
                pass
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sparql trace write failed: %s", exc)


def install() -> bool:
    """Install the wrapper if WD_SPARQL_TRACE is set.

    Returns ``True`` if the wrapper is in place after the call, ``False``
    if tracing is disabled or Trails is not importable.
    """
    global _installed
    if not _truthy(os.environ.get("WD_SPARQL_TRACE")):
        return False
    with _install_lock:
        if _installed:
            return True
        try:
            from trails.sdk import KG  # type: ignore
        except Exception as exc:  # noqa: BLE001
            logger.warning("sparql trace: Trails not importable: %s", exc)
            return False

        original_query = KG.query
        original_update = KG.update

        def _truncate(s: str, n: int = 4000) -> str:
            if len(s) <= n:
                return s
            return s[:n] + f"\n... ({len(s) - n} more chars truncated)"

        def traced_query(self, sparql, *args, **kwargs):  # type: ignore[no-redef]
            t0 = time.monotonic()
            ok = True
            rows = None
            try:
                rows = original_query(self, sparql, *args, **kwargs)
                return rows
            except Exception:
                ok = False
                raise
            finally:
                try:
                    rc = len(rows) if rows is not None else 0
                except Exception:  # noqa: BLE001
                    rc = 0
                _write_record({
                    "ts": time.time(),
                    "kind": "query",
                    "ok": ok,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 3),
                    "row_count": rc,
                    "trace_id": getattr(getattr(self, "_ctx", None), "trace_id", ""),
                    "principal": getattr(getattr(self, "_ctx", None), "principal", ""),
                    "sparql": _truncate(str(sparql).strip()),
                })

        def traced_update(self, sparql, *args, **kwargs):  # type: ignore[no-redef]
            t0 = time.monotonic()
            ok = True
            try:
                return original_update(self, sparql, *args, **kwargs)
            except Exception:
                ok = False
                raise
            finally:
                _write_record({
                    "ts": time.time(),
                    "kind": "update",
                    "ok": ok,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 3),
                    "trace_id": getattr(getattr(self, "_ctx", None), "trace_id", ""),
                    "principal": getattr(getattr(self, "_ctx", None), "principal", ""),
                    "sparql": _truncate(str(sparql).strip()),
                })

        KG.query = traced_query  # type: ignore[assignment]
        KG.update = traced_update  # type: ignore[assignment]
        _installed = True

        # Marker line at install time so the tailer sees something even
        # before any query fires.
        _write_record({
            "ts": time.time(),
            "kind": "trace_installed",
            "log_file": str(_log_path()),
        })
        logger.info("sparql trace installed: %s", _log_path())
        return True
