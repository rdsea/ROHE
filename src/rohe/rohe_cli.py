# TODO: remove main_path,default_temp_path, ... as they are just example
import json
import subprocess
import traceback

import click
import requests

from .common import rohe_utils
from .common.logger import logger
from .variable import PACKAGE_DIR, ROHE_PATH

default_temp_path = ROHE_PATH + "/temp/"
default_template_path = ROHE_PATH + "/templates/"
default_conf_path = ROHE_PATH + "/examples/agentConfig/"

headers = {"Content-Type": "application/json"}


@click.group()
@click.version_option()
def cli():
    pass


@click.group()
def start():
    pass


@click.group()
def observation():
    pass


@click.group()
def orchestration():
    pass


@observation.command()
@click.option("--app", help="application name", default="test")
@click.option("--run", help="Experiment name/id", default="experiment2")
@click.option("--user", help="application name", default="aaltosea1")
@click.option(
    "--url", help="registration url", default="http://localhost:5010/registration"
)
@click.option(
    "--output_dir", help="output_file, make sure the directory exists", default=None
)
def register_app(app, run, user, url, output_dir):
    try:
        res_data = {"application_name": app}
        res_data["run_id"] = run
        res_data["user_id"] = user

        logger.debug(res_data)
        # Send registration data to registration service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(res_data)
        )
        logger.debug(response.json())

        # get application ID from the registration service response
        res_data["app_id"] = response.json()["response"]["app_id"]

        # get QoA configuration from the registration service response
        qoa_conf = {"client": res_data, "registration_url": url}

        # Load metadata for QoA client from environment variable (optional)
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


@observation.command()
@click.option("--app", help="application name", default="dummy")
@click.option("--conf", help="configuration path", default=None)
@click.option("--url", help="registration url", default="http://localhost:5010/agent")
def start_observation_agent(app, conf, url):
    try:
        if conf is None:
            conf = default_conf_path + app + "/start.yaml"
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@observation.command()
@click.option("--app", help="application name", default="dummy")
@click.option("--conf", help="configuration path", default=None)
@click.option("--url", help="registration url", default="http://localhost:5010/agent")
def stop_observation_agent(app, conf, url):
    try:
        if conf is None:
            conf = default_conf_path + app + "/stop.yaml"
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        # load stop command from path
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        print(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@observation.command()
@click.option("--app", help="application name", default="dummy")
@click.option("--run", help="application name", default="experiment1")
@click.option("--user", help="application name", default="aaltosea1")
@click.option(
    "--url", help="registration url", default="http://localhost:5010/agent/delete"
)
def delete_app(app, run, user, url):
    try:
        res_data = {"application_name": app}
        res_data["run_id"] = run
        res_data["user_id"] = user

        logger.debug(res_data)
        # Send delete application command to registration service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(res_data)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="add_node.yaml")
@click.option(
    "--url",
    help="registration url",
    default="http://localhost:5002/management/add-node",
)
def add_node(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="add_service.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def add_service(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="get_node.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def get_node(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="get_service.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def get_service(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.error(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="remove_node.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def remove_node(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="start_orchestration.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def start_orchestration_agent(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


@orchestration.command()
@click.option("--app", help="application name", default="test")
@click.option("--conf", help="configuration path", default="stop_orchestration.yaml")
@click.option(
    "--url", help="registration url", default="http://localhost:5002/management"
)
def stop_orchestration_agent(app, conf, url):
    try:
        conf = default_template_path + "orchestration_command/" + conf
        # load agent configuration from path
        config_file = rohe_utils.load_config(conf)
        config_file["application"] = app

        # sent start command and agent configuration to agent service
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(config_file)
        )
        logger.debug(response.json())
    except Exception:
        logger.exception(traceback.print_exc())


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


cli.add_command(start)
cli.add_command(orchestration)
cli.add_command(observation)

if __name__ == "__main__":
    cli()
