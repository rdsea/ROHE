from __future__ import annotations

import subprocess

import typer

app = typer.Typer(help="Start ROHE services.")


@app.command()
def orchestration_service(
    debug: bool = typer.Option(False, "--debug", help="Run uvicorn with reload"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(5002, "--port", "-p", help="Port to bind to"),
) -> None:
    """Start the orchestration service (FastAPI + uvicorn)."""
    cmd = [
        "uvicorn",
        "rohe.service.orchestration_service_fastapi:create_orchestration_app",
        "--factory",
        "--host", host,
        "--port", str(port),
    ]
    if debug:
        cmd.append("--reload")
    subprocess.run(cmd, check=False)


@app.command()
def observation_service(
    debug: bool = typer.Option(False, "--debug", help="Run uvicorn with reload"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(5010, "--port", "-p", help="Port to bind to"),
) -> None:
    """Start the observation service (FastAPI + uvicorn)."""
    cmd = [
        "uvicorn",
        "rohe.service.observation_service_fastapi:create_observation_app",
        "--factory",
        "--host", host,
        "--port", str(port),
    ]
    if debug:
        cmd.append("--reload")
    subprocess.run(cmd, check=False)
