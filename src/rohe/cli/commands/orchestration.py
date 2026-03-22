from __future__ import annotations

import json
from pathlib import Path

import requests
import typer

from rohe.common import rohe_utils

app = typer.Typer(help="Orchestration management commands.")

HEADERS = {"Content-Type": "application/json"}
DEFAULT_MGMT_URL = "http://localhost:5002/management"


@app.command()
def add_node_from_file(
    file_path: Path = typer.Argument(..., exists=True, help="Path to node config file"),
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/add-node", "--url", help="Management URL"),
) -> None:
    """Add nodes from a config file."""
    config = rohe_utils.load_config(str(file_path))
    response = requests.post(url, headers=HEADERS, data=json.dumps(config), timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def add_service_from_file(
    file_path: Path = typer.Argument(..., exists=True, help="Path to service config file"),
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/add-service", "--url", help="Management URL"),
) -> None:
    """Add services from a config file."""
    config = rohe_utils.load_config(str(file_path))
    response = requests.post(url, headers=HEADERS, data=json.dumps(config), timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def get_nodes(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/get-all-nodes", "--url", help="Management URL"),
) -> None:
    """Retrieve all nodes."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def get_services(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/get-all-services", "--url", help="Management URL"),
) -> None:
    """Retrieve all services."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def remove_all_nodes(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/remove-all-nodes", "--url", help="Management URL"),
) -> None:
    """Remove all nodes."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def remove_all_services(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/remove-all-services", "--url", help="Management URL"),
) -> None:
    """Remove all services."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def start_agent(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/start-agent", "--url", help="Management URL"),
) -> None:
    """Start the orchestration agent."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def stop_agent(
    url: str = typer.Option(f"{DEFAULT_MGMT_URL}/stop-agent", "--url", help="Management URL"),
) -> None:
    """Stop the orchestration agent."""
    response = requests.post(url, headers=HEADERS, timeout=30)
    typer.echo(json.dumps(response.json(), indent=2))
