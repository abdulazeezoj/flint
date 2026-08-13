"""Best-effort persistence of a user's last choices (``~/.conjure/last.json``).

This is a convenience layer only, never a source of truth: an explicit
CLI flag/`--option` always wins over anything remembered here, and a
missing, corrupt, or unwritable prefs file just means "no remembered
defaults" — it must never crash generation. See PRODUCT_FLOW.md §2/§4 for
how remembered values influence (without replacing) prompt defaults in
both interactive and non-interactive mode.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PREFS_DIR = Path.home() / ".conjure"
PREFS_FILE = PREFS_DIR / "last.json"


def load_prefs() -> dict[str, Any]:
    """Best-effort read. Any problem at all (missing, unreadable, not
    valid JSON, not even an object) resolves to "no prefs" rather than
    raising."""
    try:
        data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_prefs(prefs: dict[str, Any]) -> None:
    """Best-effort write. Never raises — a failure here (e.g. a
    read-only home directory) must not break an otherwise-successful
    generation."""
    try:
        PREFS_DIR.mkdir(parents=True, exist_ok=True)
        PREFS_FILE.write_text(
            json.dumps(prefs, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError:
        pass


def get_last_framework(prefs: dict[str, Any]) -> str | None:
    value = prefs.get("last_framework")
    return value if isinstance(value, str) else None


def get_last_template(prefs: dict[str, Any], framework_id: str) -> str | None:
    last_templates = prefs.get("last_templates")
    if not isinstance(last_templates, dict):
        return None
    value = last_templates.get(framework_id)
    return value if isinstance(value, str) else None


def get_template_prefs(prefs: dict[str, Any], full_id: str) -> dict[str, Any]:
    """Return the remembered ``{options, docker, git_init, install}`` for
    a `<framework>/<template>` id, sanitized so callers never have to
    guard against a corrupt/hand-edited prefs file themselves."""
    templates = prefs.get("templates")
    entry = templates.get(full_id) if isinstance(templates, dict) else None
    if not isinstance(entry, dict):
        entry = {}

    options = entry.get("options")

    def _bool_or_none(key: str) -> bool | None:
        value = entry.get(key)
        return value if isinstance(value, bool) else None

    return {
        "options": options if isinstance(options, dict) else {},
        "docker": _bool_or_none("docker"),
        "git_init": _bool_or_none("git_init"),
        "install": _bool_or_none("install"),
    }


def record_run(
    prefs: dict[str, Any],
    *,
    framework_id: str,
    template_id: str,
    full_id: str,
    options: dict[str, Any],
    docker: bool,
    git_init: bool,
    install: bool,
) -> dict[str, Any]:
    """Return an updated copy of ``prefs`` reflecting a successful
    generation, ready to pass to `save_prefs`."""
    last_templates = dict(prefs.get("last_templates") or {})
    last_templates[framework_id] = template_id

    templates = dict(prefs.get("templates") or {})
    templates[full_id] = {
        "options": dict(options),
        "docker": docker,
        "git_init": git_init,
        "install": install,
    }

    return {
        **prefs,
        "last_framework": framework_id,
        "last_templates": last_templates,
        "templates": templates,
    }
