"""``openacad museum`` — launch the frozen 9-rung Streamlit tour."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def _find_streamlit_app() -> Path | None:
    """Find ``museum/streamlit/streamlit_app.py`` walking upwards from cwd."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    for parent in here.parents:
        c = parent / "museum" / "streamlit" / "streamlit_app.py"
        if c.exists():
            candidates.append(c)
    c2 = Path.cwd() / "museum" / "streamlit" / "streamlit_app.py"
    if c2.exists():
        candidates.append(c2)
    return candidates[0] if candidates else None


def museum(
    port: int = typer.Option(8585, "--port", help="Streamlit port."),
) -> None:
    """Launch the frozen Streamlit thesis tour. Requires the ``[museum]`` extra."""
    app_path = _find_streamlit_app()
    if app_path is None:
        console.print(
            "[red]museum/streamlit/streamlit_app.py not found[/red] — run from app/ root."
        )
        raise typer.Exit(code=1)
    console.print(f"launching streamlit on :{port}  ({app_path})")
    cmd = ["streamlit", "run", str(app_path), "--server.port", str(port)]
    rc = subprocess.run(cmd).returncode
    raise typer.Exit(code=rc)
