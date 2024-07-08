import json
import subprocess
import traceback

import click
import requests

from .common import rohe_utils
from .common.logger import logger
from .variable import PACKAGE_DIR, ROHE_PATH

default_temp_path = ROHE_PATH + "/temp/"
default_conf_path = ROHE_PATH + "/examples/agentConfig/"

headers = {"Content-Type": "application/json"}


@click.group()
@click.version_option()
def rohe_cli():
    """CLI group for ROHE commands."""
    pass


@click.group()
def start():
    """Group for starting services."""
    pass


@click.group()
def observation():
    """Group for observation related commands."""
    pass


@click.group()
def orchestration():
    """Group for orchestration related commands."""
    pass


@observation.command()
@click.option("--app", help="Application name", default="test")
@click.option("--run", help="Experiment name/id", default="experiment2")
@click.option("--user", help="User name", default="aaltosea1")
@click.option(
    "--url", help="Registration URL", default="http://localhost:5010/registration"
)
@click.option(
    "--output_dir", help="Output directory. Ensure the directory exists.", default=None
)
def register_app(app, run, user, url, output_dir):
    """
    Register an application with the observation service.
    """
    try:
        res_data = {"application_name": app, "run_id": run, "user_id": user}

        logger.debug(res_data)
        response = requests.post(url, headers=headers, data=json.dumps(res_data))
        logger.debug(response.json())

        res_data["app_id"] = response.json()["response"]["app_id"]
        qoa_conf = {"client": res_data, "registration_url": url}
        qoa_conf["client"] = rohe_utils.load_qoa_conf_env(qoa_conf["client"])

        if output_dir is None:
            output_dir = default_temp_path + app
        else:
            output_dir += app

        if rohe_utils.make_folder(output_dir):
            file_path = output_dir + "/qoa_config.yaml"
            rohe_utils.to_yaml(file_path, qoa_conf)

        logger.debug(qoa_conf)
    except Exception:
        logger.exception(traceback.print_exc())


@observation.command("start_agent")
@click.option("--app", help="Application name", default="dummy")
@click.option("--conf", help="Configuration path", default=None)
@click.option("--url", help="Registration URL", default="http://localhost:5010/agent")
def start_observation_agent(app, conf, url):
    """
    Start an observation agent.
    """
    try:
        if conf is None:
            conf = default_conf_path + app + "/start.yaml"

        config_file = rohe_utils.load_config(conf)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@observation.command("stop_agent")
@click.option("--app", help="Application name", default="dummy")
@click.option("--conf", help="Configuration path", default=None)
@click.option("--url", help="Registration URL", default="http://localhost:5010/agent")
def stop_observation_agent(app, conf, url):
    """
    Stop an observation agent.
    """
    try:
        if conf is None:
            conf = default_conf_path + app + "/stop.yaml"

        config_file = rohe_utils.load_config(conf)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        print(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@observation.command()
@click.option("--app", help="Application name", default="dummy")
@click.option("--run", help="Experiment name", default="experiment1")
@click.option("--user", help="User name", default="aaltosea1")
@click.option(
    "--url", help="Registration URL", default="http://localhost:5010/agent/delete"
)
def delete_app(app, run, user, url):
    """
    Delete an application from the observation service.
    """
    try:
        res_data = {"application_name": app, "run_id": run, "user_id": user}

        logger.debug(res_data)
        response = requests.post(url, headers=headers, data=json.dumps(res_data))
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--url",
    help="Node management URL",
    default="http://localhost:5002/management/add-node",
)
def add_node(file_path, url):
    """
    Add a list of nodes to the orchestration service.
    """
    try:
        config_file = rohe_utils.load_config(file_path)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Error in adding node")


@orchestration.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--url",
    help="Service management URL",
    default="http://localhost:5002/management/add-service",
)
def add_service(file_path, url):
    """
    Add a list of services to the orchestration service.
    """
    try:
        config_file = rohe_utils.load_config(file_path)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Error in adding service")


@orchestration.command()
@click.option(
    "--url",
    help="Node management URL",
    default="http://localhost:5002/management/get-all-nodes",
)
def get_node(url):
    """
    Retrieve all nodes from the orchestration service.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Error in getting node")


@orchestration.command()
@click.option(
    "--url",
    help="Service management URL",
    default="http://localhost:5002/management/get-all-services",
)
def get_service(url):
    """
    Retrieve all services from the orchestration service.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Error in getting service")


@orchestration.command()
@click.option(
    "--url",
    help="Node management URL",
    default="http://localhost:5002/management/remove-all-nodes",
)
def remove_all_nodes(url):
    """
    Remove all nodes from the orchestration service.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Remove all nodes failed")


@orchestration.command()
@click.option(
    "--url",
    help="Service management URL",
    default="http://localhost:5002/management/remove-all-services",
)
def remove_all_services(url):
    """
    Remove all services from the orchestration service.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Remove all services failed")


@orchestration.command("start_agent")
@click.option(
    "--url",
    help="Agent management URL",
    default="http://localhost:5002/management/start-agent",
)
def start_orchestration_agent(url):
    """
    Start the orchestration agent.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Failed to start orchestration agent")


@orchestration.command("stop_agent")
@click.option(
    "--url",
    help="Agent management URL",
    default="http://localhost:5002/management/stop-agent",
)
def stop_orchestration_agent(url):
    """
    Stop the orchestration agent.
    """
    try:
        response = requests.post(url, headers=headers)
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Failed to stop orchestration agent")


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
            "orchestration_service:app",
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
            "observation_service:app",
        ]
    )
    subprocess.run(command, check=False)


rohe_cli.add_command(start)
rohe_cli.add_command(orchestration)
rohe_cli.add_command(observation)

if __name__ == "__main__":
    rohe_cli()
