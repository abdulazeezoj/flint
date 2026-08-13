"""Turn a free-text project name into a safe directory slug and a valid,
importable Python package name.

Pure functions, no I/O — see PRODUCT_ARCH.md §6 for why this module is
kept separate and exhaustively unit tested.
"""

from __future__ import annotations

import keyword
import re
import sys

from flint.errors import FlintUserError

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")

# Stdlib/top-level module names a generated package would shadow and
# confuse imports for. Not exhaustive — just the ones a new user is
# actually likely to type.
_RESERVED_NAMES = {
    "test",
    "tests",
    "types",
    "typing",
    "os",
    "sys",
    "json",
    "string",
    "random",
    "email",
    "logging",
    "queue",
    "socket",
    "unittest",
    "flint",
}


def _normalize(raw: str) -> str:
    """Lowercase and collapse anything that isn't [a-z0-9] into single hyphens."""
    normalized = _NON_WORD_RE.sub("-", raw.strip().lower()).strip("-")
    return normalized


def slugify(raw: str) -> str:
    """Derive a filesystem/directory-safe slug, e.g. "My Api!" -> "my-api"."""
    slug = _normalize(raw)
    if not slug:
        raise FlintUserError(
            f"'{raw}' does not contain any letters or numbers — "
            "please choose a different project name."
        )
    return slug


def package_name_from_slug(slug: str) -> str:
    """Derive a valid, importable Python package name from a slug.

    Only the mechanical, documented transforms happen here (PRODUCT_FLOW.md
    §3): hyphens to underscores, and a leading underscore if the result
    would otherwise start with a digit. Keyword/stdlib collisions are
    *rejected* by ``validate_project_name`` rather than silently patched
    here — see PRODUCT_FLOW.md §3.
    """
    name = slug.replace("-", "_")
    if name[0].isdigit():
        name = f"_{name}"
    return name


def validate_project_name(raw: str) -> tuple[str, str]:
    """Validate a raw project name and return ``(slug, package_name)``.

    Raises ``FlintUserError`` with a specific, user-facing reason on any
    invalid input, per PRODUCT_FLOW.md §3 — never silently mutates a name
    into something the user didn't ask for and didn't see.
    """
    slug = slugify(raw)
    package_name = package_name_from_slug(slug)

    if not package_name.isidentifier():
        raise FlintUserError(
            f"'{raw}' cannot be turned into a valid Python package name "
            f"(got '{package_name}')."
        )
    if keyword.iskeyword(package_name) or keyword.issoftkeyword(package_name):
        raise FlintUserError(
            f"'{package_name}' is a Python keyword and can't be used as a "
            "package name — please choose a different project name."
        )
    if package_name in _RESERVED_NAMES or package_name in sys.stdlib_module_names:
        raise FlintUserError(
            f"'{package_name}' shadows a Python standard library module — "
            "please choose a different project name."
        )
    return slug, package_name
