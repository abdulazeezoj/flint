"""Post-generation steps: git init, `uv sync`, and the final summary.

Each step is isolated behind its own function and never raises on a
missing binary — a missing `git`/`uv` warns and leaves the generated
project in a valid, runnable state (PRODUCT_FLOW.md §5).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def git_init(target_dir: Path) -> bool:
    """Initialize a git repo with an initial commit. Returns success."""
    if shutil.which("git") is None:
        console.print("[yellow]![/yellow] git not found — skipping git init.")
        return False
    try:
        subprocess.run(
            ["git", "init", "-q"], cwd=target_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=target_dir, check=True, capture_output=True
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=flint",
                "-c",
                "user.email=flint@localhost",
                "commit",
                "-q",
                "-m",
                "Initial commit from flint",
            ],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        console.print(f"[yellow]![/yellow] git init failed: {exc.stderr.decode().strip()}")
        return False


def install_dependencies(target_dir: Path) -> bool:
    """Run `uv sync` in the generated project. Returns success."""
    if shutil.which("uv") is None:
        console.print("[yellow]![/yellow] uv not found — skipping dependency install.")
        return False
    try:
        with console.status("Installing dependencies (uv sync)..."):
            subprocess.run(
                ["uv", "sync"], cwd=target_dir, check=True, capture_output=True
            )
        return True
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[yellow]![/yellow] uv sync failed: {exc.stderr.decode().strip()}"
        )
        return False


def print_summary(
    *,
    project_name: str,
    slug: str,
    package_name: str,
    template_id: str,
    target_dir: Path,
    created: list[Path],
    git_ok: bool,
    installed_ok: bool,
    installed_requested: bool,
) -> None:
    console.print()
    console.print(f"Creating [bold]{slug}/[/bold] from {template_id}...")
    for path in created:
        console.print(f"  [green]✔[/green] {path.as_posix()}")

    if git_ok:
        console.print("[green]✔[/green] Initialized git repository")
    if installed_requested and installed_ok:
        console.print("[green]✔[/green] Installed dependencies (uv sync)")

    console.print()
    console.print(f"[bold green]Success![/bold green] Created {project_name} at ./{slug}")
    console.print()
    console.print("Next steps:")
    console.print(f"  cd {slug}")
    if not installed_ok:
        console.print("  uv sync")
    console.print(f"  uv run fastapi dev src/{package_name}/main.py")
    console.print()
    console.print("Then open [link]http://127.0.0.1:8000[/link]")
