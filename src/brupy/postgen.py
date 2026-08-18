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
                "user.name=brupy",
                "-c",
                "user.email=brupy@localhost",
                "commit",
                "-q",
                "-m",
                "Initial commit from brupy",
            ],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        console.print(f"[yellow]![/yellow] git init failed: {exc.stderr.decode().strip()}")
        return False


def _run_install(
    target_dir: Path, *, binary: str, cmd: list[str], status: str, failure_label: str
) -> bool:
    """Shared shape for `install_dependencies`/`install_frontend_dependencies`:
    check the binary exists, run `cmd` under a status spinner, and treat
    any failure as best-effort (warn, never raise). Returns success."""
    if shutil.which(binary) is None:
        console.print(f"[yellow]![/yellow] {binary} not found — skipping {failure_label}.")
        return False
    try:
        with console.status(status):
            subprocess.run(cmd, cwd=target_dir, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[yellow]![/yellow] {' '.join(cmd)} failed: {exc.stderr.decode().strip()}"
        )
        return False


def install_dependencies(target_dir: Path) -> bool:
    """Run `uv sync` in the generated project. Returns success."""
    return _run_install(
        target_dir,
        binary="uv",
        cmd=["uv", "sync"],
        status="Installing dependencies (uv sync)...",
        failure_label="dependency install",
    )


def install_frontend_dependencies(target_dir: Path) -> bool:
    """Run `bun install` in the generated project, if it has a
    `package.json` (e.g. `full-stack`'s `css=tailwind` Tailwind CSS +
    daisyUI toolchain). A no-op returning `False` if there's no
    `package.json` at all — most generated projects don't have one, and
    that's not a failure worth warning about. Returns success."""
    if not (target_dir / "package.json").is_file():
        return False
    return _run_install(
        target_dir,
        binary="bun",
        cmd=["bun", "install"],
        status="Installing frontend dependencies (bun install)...",
        failure_label="frontend dependency install",
    )


def print_summary(
    *,
    project_name: str,
    slug: str,
    template_full_id: str,
    target_dir: Path,
    created: list[Path],
    git_ok: bool,
    installed_ok: bool,
    installed_requested: bool,
    run_command: str,
    options: dict[str, object] | None = None,
    frontend_installed_ok: bool = False,
) -> None:
    console.print()
    if options:
        rendered = ", ".join(f"{key}={value}" for key, value in options.items())
        console.print(f"Options: {rendered}")
    console.print(f"Creating [bold]{slug}/[/bold] from {template_full_id}...")
    for path in created:
        console.print(f"  [green]✔[/green] {path.as_posix()}")

    has_frontend = Path("package.json") in created
    if git_ok:
        console.print("[green]✔[/green] Initialized git repository")
    if installed_requested and installed_ok:
        console.print("[green]✔[/green] Installed dependencies (uv sync)")
    if installed_requested and has_frontend and frontend_installed_ok:
        console.print("[green]✔[/green] Installed frontend dependencies (bun install)")

    console.print()
    console.print(f"[bold green]Success![/bold green] Created {project_name} at ./{slug}")
    console.print()
    console.print("Next steps:")
    console.print(f"  cd {slug}")
    if not installed_ok:
        console.print("  uv sync")
    if has_frontend and not frontend_installed_ok:
        console.print("  bun install")
    if Path("dev.py") in created:
        console.print("  uv run dev.py")
    else:
        console.print(f"  {run_command}")
    console.print()
    console.print("Then open [link]http://127.0.0.1:8000[/link]")

    if Path("Dockerfile") in created:
        console.print()
        console.print("Or with Docker:")
        console.print(f"  docker build -t {slug} .")
        console.print(f"  docker run -p 8000:8000 {slug}")
