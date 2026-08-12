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
from flint import generator, postgen, prompts
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
        _run_new(name=None, framework=None, git=None, install=None, yes=False, force=False)


@app.command()
def new(
    name: Annotated[
        Optional[str], typer.Argument(help="Project name, e.g. 'my-api'.")
    ] = None,
    framework: Annotated[
        Optional[str],
        typer.Option(help="Template to use, e.g. 'fastapi-hello-world'."),
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
) -> None:
    """Generate a new project."""
    _run_new(name=name, framework=framework, git=git, install=install, yes=yes, force=force)


def _run_new(
    *,
    name: Optional[str],
    framework: Optional[str],
    git: Optional[bool],
    install: Optional[bool],
    yes: bool,
    force: bool,
) -> None:
    interactive = sys.stdin.isatty() and not yes

    try:
        project_name, slug, package_name = prompts.prompt_project_name(name, interactive)

        target_dir = Path.cwd() / slug
        if target_dir.exists() and any(target_dir.iterdir()) and not force:
            raise FlintUserError(
                f"Directory '{slug}' already exists and is not empty. "
                "Use --force to generate into it anyway."
            )

        templates = generator.list_templates()
        template_id = prompts.prompt_framework(framework, templates, interactive)

        if interactive:
            console.print("Using uv to manage dependencies.")

        git_init = prompts.prompt_git_init(git, interactive)
        install_now = prompts.prompt_install(install, interactive)

        answers = generator.Answers(
            project_name=project_name,
            slug=slug,
            package_name=package_name,
            framework=template_id,
            git_init=git_init,
            install=install_now,
        )
        created = generator.render(template_id, target_dir, answers, force=force)

        git_ok = postgen.git_init(target_dir) if git_init else False
        installed_ok = postgen.install_dependencies(target_dir) if install_now else False

        postgen.print_summary(
            project_name=project_name,
            slug=slug,
            package_name=package_name,
            template_id=template_id,
            target_dir=target_dir,
            created=created,
            git_ok=git_ok,
            installed_ok=installed_ok,
            installed_requested=install_now,
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
