"""Interactive wizard steps (PRODUCT_FLOW.md §2).

Every function here follows the same contract: if a value was already
supplied (via a CLI flag), it's returned as-is with no prompt. Otherwise,
in non-interactive mode, the documented default is used. Only in
interactive mode does the function actually ask.
"""

from __future__ import annotations

from typing import Any

import questionary
from rich.console import Console

from flint.errors import FlintUserError
from flint.generator import FrameworkMeta, TemplateMeta, when_matches
from flint.naming import validate_project_name

console = Console()

DEFAULT_PROJECT_NAME = "my-app"

_TRUTHY = {"true", "1", "yes", "y"}
_FALSY = {"false", "0", "no", "n"}


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
    default_id: str | None = None,
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
    default = default_id if default_id in {e.id for e in enabled} else enabled[0].id

    if not interactive:
        return default

    choices = [
        questionary.Choice(
            title=e.label if e.enabled else f"{e.label} (coming soon)",
            value=e.id,
            disabled="coming soon" if not e.enabled else None,
        )
        for e in entries
    ]
    answer = questionary.select(question, choices=choices, default=default).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_framework(
    framework: str | None,
    frameworks: list[FrameworkMeta],
    interactive: bool,
    default_id: str | None = None,
) -> str:
    return _select_enabled(
        "Which framework?", framework, frameworks, interactive, "--framework", default_id
    )


def prompt_template(
    template: str | None,
    templates: list[TemplateMeta],
    interactive: bool,
    default_id: str | None = None,
) -> str:
    return _select_enabled(
        "Which template?", template, templates, interactive, "--template", default_id
    )


def prompt_docker(
    docker: bool | None, interactive: bool, remembered: bool | None = None
) -> bool:
    if docker is not None:
        return docker
    default = remembered if remembered is not None else False
    if not interactive:
        return default
    answer = questionary.confirm("Add a Dockerfile?", default=default).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_git_init(
    git_init: bool | None, interactive: bool, remembered: bool | None = None
) -> bool:
    if git_init is not None:
        return git_init
    default = remembered if remembered is not None else True
    if not interactive:
        return default
    answer = questionary.confirm("Initialize a git repository?", default=default).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_install(
    install: bool | None, interactive: bool, remembered: bool | None = None
) -> bool:
    if install is not None:
        return install
    default = remembered if remembered is not None else True
    if not interactive:
        return default
    answer = questionary.confirm(
        "Install dependencies with uv now?", default=default
    ).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def prompt_force_overwrite(slug: str, force: bool, interactive: bool) -> bool:
    """Whether generation should proceed into a non-empty target directory.

    Only called once the caller has already confirmed the directory is
    non-empty. Already `--force`d or non-interactive: returned as-is,
    no prompt — a non-interactive run can't prompt, so the caller hard-
    errors instead (PRODUCT_FLOW.md §5). Interactive and not yet forced:
    ask before overwriting rather than failing outright.
    """
    if force or not interactive:
        return force
    answer = questionary.confirm(
        f"Directory '{slug}' already exists and is not empty. Overwrite?",
        default=False,
    ).ask()
    if answer is None:
        raise FlintUserError("Cancelled.")
    return answer


def parse_option_flags(raw_options: list[str]) -> dict[str, str]:
    """Parse repeatable ``--option key=value`` flags into a dict."""
    parsed: dict[str, str] = {}
    for item in raw_options:
        if "=" not in item:
            raise FlintUserError(f"--option '{item}' must be in key=value form.")
        key, _, value = item.partition("=")
        parsed[key] = value
    return parsed


def _parse_bool_flag(key: str, raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    raise FlintUserError(f"'{raw}' is not a valid boolean for --option {key} (use true/false).")


def prompt_template_options(
    template: TemplateMeta,
    provided: dict[str, str],
    interactive: bool,
    last: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve every option a template declares, in declared order.

    Declared order matters: a later option's ``when`` can only see
    already-resolved earlier options (PRODUCT_ARCH.md documents this as a
    template-authoring requirement).

    ``last`` is a remembered ``{key: value}`` map (PRODUCT_FLOW.md §2/§4)
    used as the fallback default in place of the template's own
    ``default`` — for both the interactive prompt's preselection and the
    non-interactive fallback value. A remembered value that's no longer
    valid for this option (stale choice, wrong type) is silently ignored
    in favor of the template's own default.
    """
    unknown = set(provided) - {option.key for option in template.options}
    if unknown:
        raise FlintUserError(
            f"Unknown option(s) for {template.full_id}: {', '.join(sorted(unknown))}."
        )

    last = last or {}
    resolved: dict[str, Any] = {}
    for option in template.options:
        if option.key in provided:
            raw = provided[option.key]
            if option.type == "confirm":
                resolved[option.key] = _parse_bool_flag(option.key, raw)
            else:
                valid_values = {choice["value"] for choice in option.choices}
                if raw not in valid_values:
                    raise FlintUserError(
                        f"'{raw}' is not a valid value for --option {option.key}. "
                        f"Available: {', '.join(sorted(valid_values))}."
                    )
                resolved[option.key] = raw
            continue

        if not when_matches(option.when, resolved):
            resolved[option.key] = option.resolved_skip_value
            continue

        remembered = last.get(option.key)
        if option.type == "confirm":
            default = remembered if isinstance(remembered, bool) else bool(option.default)
        else:
            valid_values = {choice["value"] for choice in option.choices}
            default = remembered if remembered in valid_values else option.default

        if not interactive:
            resolved[option.key] = default
            continue

        if option.type == "confirm":
            answer = questionary.confirm(option.label, default=default).ask()
        else:
            choices = [
                questionary.Choice(title=choice["label"], value=choice["value"])
                for choice in option.choices
            ]
            answer = questionary.select(
                option.label, choices=choices, default=default
            ).ask()
        if answer is None:
            raise FlintUserError("Cancelled.")
        resolved[option.key] = answer

    return resolved
