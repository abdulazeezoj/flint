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
from flint.generator import FrameworkMeta, TemplateMeta
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


def _select_enabled(
    question: str,
    value: str | None,
    entries: list[FrameworkMeta] | list[TemplateMeta],
    interactive: bool,
    not_found_label: str,
) -> str:
    by_id = {e.id: e for e in entries}

    if value is not None:
        if value not in by_id:
            raise FlintUserError(
                f"Unknown {not_found_label} '{value}'. "
                f"Available: {', '.join(e.id for e in entries)}."
            )
        if not by_id[value].enabled:
            raise FlintUserError(f"'{value}' isn't available yet.")
        return value

    enabled = [e for e in entries if e.enabled]
    if not interactive:
        return enabled[0].id

    choices = [
        questionary.Choice(
            title=e.label if e.enabled else f"{e.label} (coming soon)",
            value=e.id,
            disabled="coming soon" if not e.enabled else None,
        )
        for e in entries
    ]
    answer = questionary.select(question, choices=choices).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_framework(
    framework: str | None, frameworks: list[FrameworkMeta], interactive: bool
) -> str:
    return _select_enabled(
        "Which framework?", framework, frameworks, interactive, "--framework"
    )


def prompt_template(
    template: str | None, templates: list[TemplateMeta], interactive: bool
) -> str:
    return _select_enabled(
        "Which template?", template, templates, interactive, "--template"
    )


def prompt_docker(docker: bool | None, interactive: bool) -> bool:
    if docker is not None:
        return docker
    if not interactive:
        return False
    answer = questionary.confirm("Add a Dockerfile?", default=False).ask()
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
