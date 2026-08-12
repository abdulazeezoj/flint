"""Interactive wizard steps (PRODUCT_FLOW.md §2).

Every function here follows the same contract: if a value was already
supplied (via a CLI flag), it's returned as-is with no prompt. Otherwise,
in non-interactive mode, the documented default is used. Only in
interactive mode does the function actually ask.
"""

from __future__ import annotations

import questionary
from rich.console import Console

from flint.errors import FlintUserError
from flint.generator import TemplateMeta
from flint.naming import validate_project_name

console = Console()

DEFAULT_PROJECT_NAME = "my-app"


def prompt_project_name(name: str | None, interactive: bool) -> tuple[str, str, str]:
    """Return ``(project_name, slug, package_name)``."""
    if name is not None:
        slug, package_name = validate_project_name(name)
        return name, slug, package_name

    if not interactive:
        slug, package_name = validate_project_name(DEFAULT_PROJECT_NAME)
        return DEFAULT_PROJECT_NAME, slug, package_name

    while True:
        answer = questionary.text(
            "What is your project named?", default=DEFAULT_PROJECT_NAME
        ).ask()
        if answer is None:
            raise FlintUserError("Cancelled.")
        try:
            slug, package_name = validate_project_name(answer)
            return answer, slug, package_name
        except FlintUserError as exc:
            console.print(f"[red]✖[/red] {exc}")


def prompt_framework(
    framework: str | None, templates: list[TemplateMeta], interactive: bool
) -> str:
    by_id = {t.id: t for t in templates}

    if framework is not None:
        if framework not in by_id:
            raise FlintUserError(
                f"Unknown --framework '{framework}'. "
                f"Available: {', '.join(t.id for t in templates)}."
            )
        if not by_id[framework].enabled:
            raise FlintUserError(f"'{framework}' isn't available yet.")
        return framework

    enabled = [t for t in templates if t.enabled]
    if not interactive:
        return enabled[0].id

    choices = [
        questionary.Choice(
            title=t.label if t.enabled else f"{t.label} (coming soon)",
            value=t.id,
            disabled="coming soon" if not t.enabled else None,
        )
        for t in templates
    ]
    answer = questionary.select("Which framework?", choices=choices).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_git_init(git_init: bool | None, interactive: bool) -> bool:
    if git_init is not None:
        return git_init
    if not interactive:
        return True
    answer = questionary.confirm("Initialize a git repository?", default=True).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_install(install: bool | None, interactive: bool) -> bool:
    if install is not None:
        return install
    if not interactive:
        return True
    answer = questionary.confirm(
        "Install dependencies with uv now?", default=True
    ).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer
