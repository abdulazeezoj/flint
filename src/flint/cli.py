"""The `flint` command-line app.

See PRODUCT_FLOW.md §1 for the entry-point table this implements: bare
`flint` behaves like `flint new` (an interactive wizard), `flint new
NAME --flags...` skips prompts for anything a flag already answers, and
`--yes` / a non-TTY stdin skips prompting entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from flint import __version__
from flint import generator, postgen, prefs, prompts
from flint.errors import FlintUserError

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", help="Show the version and exit.")
    ] = False,
) -> None:
    """Flint — interactive project scaffolding for Python frameworks."""
    if version:
        console.print(f"flint {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        _run_new(
            name=None,
            framework=None,
            template=None,
            option=[],
            docker=None,
            git=None,
            install=None,
            yes=False,
            force=False,
            remember=True,
        )


@app.command()
def new(
    name: Annotated[
        Optional[str], typer.Argument(help="Project name, e.g. 'my-api'.")
    ] = None,
    framework: Annotated[
        Optional[str], typer.Option(help="Framework to use, e.g. 'fastapi'.")
    ] = None,
    template: Annotated[
        Optional[str],
        typer.Option(help="Template variant within the framework, e.g. 'hello-world'."),
    ] = None,
    option: Annotated[
        list[str],
        typer.Option(
            "--option",
            "-o",
            help=(
                "Set a template-specific option as key=value (repeatable), "
                "e.g. -o database=postgres -o orm=sqlmodel. See the wizard "
                "or the template's README for available keys."
            ),
        ),
    ] = [],  # noqa: B006 - Typer's documented pattern for repeatable options
    docker: Annotated[
        Optional[bool],
        typer.Option("--docker/--no-docker", help="Add a Dockerfile."),
    ] = None,
    git: Annotated[
        Optional[bool],
        typer.Option("--git/--no-git", help="Initialize a git repository."),
    ] = None,
    install: Annotated[
        Optional[bool],
        typer.Option("--install/--no-install", help="Install dependencies with uv."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Accept defaults for anything not given as a flag."
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force", help="Generate even if the target directory already exists."
        ),
    ] = False,
    remember: Annotated[
        bool,
        typer.Option(
            "--remember/--no-remember",
            help=(
                "Remember these choices in ~/.flint/last.json as the "
                "default for next time (framework/template + per-template "
                "options, docker, git, install). Explicit flags/--option "
                "always win regardless."
            ),
        ),
    ] = True,
) -> None:
    """Generate a new project."""
    _run_new(
        name=name,
        framework=framework,
        template=template,
        option=option,
        docker=docker,
        git=git,
        install=install,
        yes=yes,
        force=force,
        remember=remember,
    )


def _run_new(
    *,
    name: Optional[str],
    framework: Optional[str],
    template: Optional[str],
    option: list[str],
    docker: Optional[bool],
    git: Optional[bool],
    install: Optional[bool],
    yes: bool,
    force: bool,
    remember: bool,
) -> None:
    interactive = sys.stdin.isatty() and not yes
    stored_prefs = prefs.load_prefs() if remember else {}

    try:
        project_name, slug, package_name = prompts.prompt_project_name(name, interactive)

        target_dir = Path.cwd() / slug
        if target_dir.exists() and any(target_dir.iterdir()) and not force:
            raise FlintUserError(
                f"Directory '{slug}' already exists and is not empty. "
                "Use --force to generate into it anyway."
            )

        frameworks = generator.list_frameworks()
        framework_id = prompts.prompt_framework(
            framework,
            frameworks,
            interactive,
            default_id=prefs.get_last_framework(stored_prefs),
        )

        chosen_framework = generator.get_framework(framework_id)

        templates = generator.list_templates(framework_id)
        template_id = prompts.prompt_template(
            template,
            templates,
            interactive,
            default_id=prefs.get_last_template(stored_prefs, framework_id),
        )

        chosen_template = generator.get_template(framework_id, template_id)
        remembered = prefs.get_template_prefs(stored_prefs, chosen_template.full_id)

        provided_options = prompts.parse_option_flags(option)
        resolved_options = prompts.prompt_template_options(
            chosen_template, provided_options, interactive, last=remembered["options"]
        )

        docker_requested = prompts.prompt_docker(
            docker, interactive, remembered=remembered["docker"]
        )
        if docker_requested and not chosen_template.supports_docker:
            console.print(
                f"[yellow]![/yellow] {chosen_template.full_id} doesn't support "
                "--docker yet — skipping the Dockerfile."
            )
            docker_requested = False

        if interactive:
            console.print("Using uv to manage dependencies.")

        git_init = prompts.prompt_git_init(git, interactive, remembered=remembered["git_init"])
        install_now = prompts.prompt_install(install, interactive, remembered=remembered["install"])

        answers = generator.Answers(
            project_name=project_name,
            slug=slug,
            package_name=package_name,
            framework=framework_id,
            template=template_id,
            git_init=git_init,
            install=install_now,
            docker=docker_requested,
            options=resolved_options,
        )
        created = generator.render(framework_id, template_id, target_dir, answers, force=force)

        if remember:
            prefs.save_prefs(
                prefs.record_run(
                    stored_prefs,
                    framework_id=framework_id,
                    template_id=template_id,
                    full_id=chosen_template.full_id,
                    options=resolved_options,
                    docker=docker_requested,
                    git_init=git_init,
                    install=install_now,
                )
            )

        git_ok = postgen.git_init(target_dir) if git_init else False
        installed_ok = postgen.install_dependencies(target_dir) if install_now else False

        postgen.print_summary(
            project_name=project_name,
            slug=slug,
            template_full_id=chosen_template.full_id,
            target_dir=target_dir,
            created=created,
            git_ok=git_ok,
            installed_ok=installed_ok,
            installed_requested=install_now,
            run_command=chosen_framework.run_command.format(package_name=package_name),
            options=resolved_options,
        )
    except FlintUserError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level safety net, see errors.py
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(2) from None


def main() -> None:
    app()


if __name__ == "__main__":
    main()
