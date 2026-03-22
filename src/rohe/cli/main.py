from __future__ import annotations

import typer

from rohe.cli.commands.observation import app as observation_app
from rohe.cli.commands.orchestration import app as orchestration_app
from rohe.cli.commands.start import app as start_app

app = typer.Typer(
    name="rohe",
    help="ROHE: Orchestration framework for End-to-End ML Serving on Heterogeneous Edge",
    no_args_is_help=True,
)

app.add_typer(start_app, name="start")
app.add_typer(orchestration_app, name="orchestration")
app.add_typer(observation_app, name="observation")


@app.callback()
def main() -> None:
    """ROHE CLI - manage orchestration, observation, and ML inference services."""


if __name__ == "__main__":
    app()
