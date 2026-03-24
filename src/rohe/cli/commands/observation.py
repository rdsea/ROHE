from __future__ import annotations

import json
import os

import requests
import typer

from rohe.common import rohe_utils

app = typer.Typer(help="Observation management commands.")

HEADERS = {"Content-Type": "application/json"}
DEFAULT_REG_URL = "http://localhost:5010/registration"
DEFAULT_AGENT_URL = "http://localhost:5010/agent"


def _get_rohe_path() -> str:
    path = os.environ.get("ROHE_PATH")
    if path is None:
        raise typer.BadParameter("ROHE_PATH environment variable is not set")
    return path


@app.command()
def register_app(
    app_name: str = typer.Option("test", "--app", help="Application name"),
    run: str = typer.Option("experiment1", "--run", help="Experiment name/id"),
    user: str = typer.Option("aaltosea1", "--user", help="User name"),
    url: str = typer.Option(DEFAULT_REG_URL, "--url", help="Registration URL"),
    output_dir: str | None = typer.Option(
        None, "--output-dir", help="Output directory"
    ),
) -> None:
    """Register an application with the observation service."""
    res_data = {"application_name": app_name, "run_id": run, "user_id": user}
    typer.echo(json.dumps(res_data))

    response = requests.post(
        url, headers=HEADERS, data=json.dumps(res_data), timeout=30
    )
    typer.echo(json.dumps(response.json(), indent=2))

    resp_json = response.json()
    res_data["app_id"] = resp_json["response"]["app_id"]
    qoa_conf = {"client": res_data, "registration_url": url}
    qoa_conf["client"] = rohe_utils.load_qoa_conf_env(qoa_conf["client"])

    if output_dir is None:
        output_dir = _get_rohe_path() + "/temp/" + app_name
    else:
        output_dir += app_name

    if rohe_utils.make_folder(output_dir):
        file_path = output_dir + "/qoa_config.yaml"
        rohe_utils.to_yaml(file_path, qoa_conf)

    typer.echo(json.dumps(qoa_conf, indent=2, default=str))


@app.command()
def delete_app(
    app_name: str = typer.Option("dummy", "--app", "-a", help="Application name"),
    run: str = typer.Option("experiment1", "--run", "-r", help="Experiment name"),
    user: str = typer.Option("aaltosea1", "--user", "-u", help="User name"),
    url: str = typer.Option(DEFAULT_REG_URL, "--url", help="Registration URL"),
) -> None:
    """Delete an application from the observation service."""
    res_data = {"application_name": app_name, "run_id": run, "user_id": user}
    response = requests.delete(
        url, headers=HEADERS, data=json.dumps(res_data), timeout=30
    )
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def start_agent(
    app_name: str = typer.Option("dummy", "--app", help="Application name"),
    conf: str | None = typer.Option(None, "--conf", help="Configuration path"),
    url: str = typer.Option(f"{DEFAULT_AGENT_URL}/start", "--url", help="Agent URL"),
) -> None:
    """Start an observation agent."""
    if conf is None:
        conf = _get_rohe_path() + "/examples/agentConfig/" + app_name + "/start.yaml"

    config_file = rohe_utils.load_config(conf)
    response = requests.post(
        url, headers=HEADERS, data=json.dumps(config_file), timeout=30
    )
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def stop_agent(
    app_name: str = typer.Option("dummy", "--app", help="Application name"),
    conf: str | None = typer.Option(None, "--conf", help="Configuration path"),
    url: str = typer.Option(f"{DEFAULT_AGENT_URL}/stop", "--url", help="Agent URL"),
) -> None:
    """Stop an observation agent."""
    if conf is None:
        conf = _get_rohe_path() + "/examples/agentConfig/" + app_name + "/stop.yaml"

    config_file = rohe_utils.load_config(conf)
    response = requests.post(
        url, headers=HEADERS, data=json.dumps(config_file), timeout=30
    )
    typer.echo(json.dumps(response.json(), indent=2))
