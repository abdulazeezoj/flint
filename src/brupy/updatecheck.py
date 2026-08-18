"""Best-effort "a newer brupy is available" notice.

This is the one deliberate exception to the "no network access required
by brupy itself" rule (PRODUCT_SPEC.md NFR, §9): a single, short,
cached PyPI lookup, silently skipped on any failure and never able to
block or fail generation. See PRODUCT_SPEC.md §9 for the full rationale
and opt-out mechanism (`BRUPY_NO_UPDATE_CHECK`/`CI` env vars, and
non-interactive runs skip it outright).
"""

from __future__ import annotations

import itertools
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from brupy import __version__

CACHE_FILE = Path.home() / ".brupy" / "update_check.json"
_CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # once a day, not once a run
_TIMEOUT_SECONDS = 1.5
_PYPI_URL = "https://pypi.org/pypi/brupy/json"


def _parse_version(version: str) -> tuple[int, int, int]:
    """`"1.2.3"` -> `(1, 2, 3)`; tolerant of anything non-numeric after
    a plain X.Y.Z (pre-releases, local version segments) by just
    ignoring it, and always exactly 3 elements (missing segments pad
    to 0) so two parsed versions are always directly comparable —
    good enough for "is there something newer," not a full PEP 440
    comparison."""
    chunks = version.split(".")[:3]
    chunks += ["0"] * (3 - len(chunks))
    parts = []
    for chunk in chunks:
        digits = "".join(itertools.takewhile(str.isdigit, chunk))
        parts.append(int(digits) if digits else 0)
    return (parts[0], parts[1], parts[2])


def _fetch_latest_version() -> str | None:
    try:
        with urllib.request.urlopen(_PYPI_URL, timeout=_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["info"]["version"]
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
        return None


def _read_cache() -> dict:
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(latest: str, checked_at: float) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps({"latest": latest, "checked_at": checked_at}), encoding="utf-8"
        )
    except OSError:
        pass


def check_for_update(*, interactive: bool) -> str | None:
    """Return a newer version string if one's worth telling the user
    about, else ``None``. Never raises. Only actually reaches the
    network once every `_CHECK_INTERVAL_SECONDS`; every other call
    within that window reads the cached result instead.
    """
    if not interactive:
        return None
    if os.environ.get("BRUPY_NO_UPDATE_CHECK") or os.environ.get("CI"):
        return None

    now = time.time()
    cache = _read_cache()
    latest = cache.get("latest")
    checked_at = cache.get("checked_at", 0)
    is_stale = not isinstance(checked_at, (int, float)) or now - checked_at > _CHECK_INTERVAL_SECONDS

    if is_stale:
        fetched = _fetch_latest_version()
        if fetched is not None:
            latest = fetched
            _write_cache(latest, now)
        elif not isinstance(latest, str):
            return None

    if not isinstance(latest, str):
        return None
    if _parse_version(latest) > _parse_version(__version__):
        return latest
    return None
