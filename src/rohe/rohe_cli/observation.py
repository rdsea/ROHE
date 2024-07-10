import json

import click
import lazy_import

from rohe.common.logger import logger
from rohe.variable import ROHE_PATH

requests = lazy_import.lazy_module("requests")

rohe_utils = lazy_import.lazy_module("rohe.common.rohe_utils")
default_temp_path = ROHE_PATH + "/temp/"
default_conf_path = ROHE_PATH + "/examples/agentConfig/"

headers = {"Content-Type": "application/json"}


@click.group()
def observation():
    """Group for observation related commands."""
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
        logger.exception("Failed to register application")


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
        logger.exception("Failed to start observation agent")


@observation.command("stop_agent")
@click.option("--app", help="Application name", default="dummy")
@click.option(
    "--url", help="Registration URL", default="http://localhost:5010/agent/start"
)
def stop_observation_agent(conf, url):
    """
    Stop an observation agent.
    """
    try:
        config_file = rohe_utils.load_config(conf)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        print(response.json())
    except Exception:
        logger.exception("Failed to stop observation agent")


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
        logger.exception("Failed to delete application")
