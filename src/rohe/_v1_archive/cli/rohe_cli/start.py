import subprocess

import click

from ..variable import PACKAGE_DIR


@click.group()
def start():
    """Group for starting services."""
    pass


@start.command()
@click.option(
    "--debug",
    is_flag=True,
    help="Run the Flask development server if set, otherwise run Gunicorn",
)
@click.option(
    "-h",
    "--host",
    default="0.0.0.0",
    help="Host to bind the server to",
    show_default=True,
)
@click.option(
    "-p", "--port", default=5002, help="Port to bind the server to", show_default=True
)
def orchestration_service(debug, host, port):
    """
    Start the orchestration service.
    """
    command = (
        [
            "flask",
            "--app",
            f"{PACKAGE_DIR}/service/orchestration_service",
            "run",
            "--debug",
            "--host",
            host,
            "--port",
            str(port),
        ]
        if debug
        else [
            "gunicorn",
            f"--bind={host}:{port}",
            "--chdir",
            f"{PACKAGE_DIR}/service",
            "orchestration_service:create_app()",
        ]
    )
    subprocess.run(command, check=False)


@start.command()
@click.option(
    "--debug",
    is_flag=True,
    help="Run the Flask development server if set, otherwise run Gunicorn",
)
@click.option(
    "-h",
    "--host",
    default="0.0.0.0",
    help="Host to bind the server to",
    show_default=True,
)
@click.option(
    "-p", "--port", default=5010, help="Port to bind the server to", show_default=True
)
def observation_service(debug, host, port):
    """
    Start the observation service.
    """
    command = (
        [
            "flask",
            "--app",
            f"{PACKAGE_DIR}/service/observation_service",
            "run",
            "--debug",
            "--host",
            host,
            "--port",
            str(port),
        ]
        if debug
        else [
            "gunicorn",
            f"--bind={host}:{port}",
            "--chdir",
            f"{PACKAGE_DIR}/service",
            "observation_service:create_app()",
        ]
    )
    subprocess.run(command, check=False)
