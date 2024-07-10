import json

import click
import lazy_import

from rohe.common.logger import logger

rohe_utils = lazy_import.lazy_module("rohe.common.rohe_utils")
requests = lazy_import.lazy_module("requests")
headers = {"Content-Type": "application/json"}


@click.group()
def orchestration():
    """Group for orchestration related commands."""
    pass


@orchestration.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--url",
    help="Node management URL",
    default="http://localhost:5002/management/add-node",
)
def add_node_from_file(file_path, url):
    """
    Add a list of nodes to the orchestration service defined in file.
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
def add_service_from_file(file_path, url):
    """
    Add a list of services to the orchestration service defined in file.
    """
    try:
        config_file = rohe_utils.load_config(file_path)
        response = requests.post(url, headers=headers, data=json.dumps(config_file))
        print(json.dumps(response.json(), indent=2))
    except Exception:
        logger.exception("Error in adding service")


@orchestration.command()
def add_node():
    """
    Interactive adding new node to the orchestration service.
    """
    data = {"data": {}}

    while True:
        node_id = click.prompt("Enter node ID (e.g., node1, node10)", type=str)
        node_name = click.prompt("Enter node name (e.g., RaspberryPi_01)", type=str)
        frequency = click.prompt("Enter frequency in GHz", type=float)
        mac_address = click.prompt(
            "Enter MAC address (e.g., 00.1A.3F.F1.4C.C6)", type=str
        )
        cpu_capacity = click.prompt("Enter CPU capacity", type=int)
        cpu_used = click.prompt("Enter CPU used", type=int)
        core_capacity_count = click.prompt("Enter number of core capacities", type=int)
        # NOTE: Here I assume that no core is used before adding node
        cores_capacity = [100 for _ in range(core_capacity_count)]
        cores_used = [0 for _ in range(core_capacity_count)]

        memory_rss_capacity = click.prompt("Enter RSS capacity", type=int)
        memory_rss_used = click.prompt("Enter RSS used", type=int)
        memory_vms_capacity = click.prompt("Enter VMS capacity", type=int)
        memory_vms_used = click.prompt("Enter VMS used", type=int)
        status = "running"

        accelerator = {}
        add_accelerator = click.confirm("Does this node have an accelerator?")
        if add_accelerator:
            # NOTE: Assume node only have 1 accelerator
            accelerator_id = "GPU0"
            accelerator_type = click.prompt(
                "Enter accelerator type",
                type=click.Choice(["gpu", "tpu"], case_sensitive=False),
            )
            accelerator_capacity = click.prompt("Enter accelerator capacity", type=int)
            accelerator_core = click.prompt("Enter accelerator core count", type=int)
            accelerator_mode = click.prompt("Enter accelerator mode", type=str)
            accelerator_used = click.prompt("Enter accelerator used", type=int)
            accelerator = {
                accelerator_id: {
                    "accelerator_type": accelerator_type,
                    "capacity": accelerator_capacity,
                    "core": accelerator_core,
                    "mode": accelerator_mode,
                    "used": accelerator_used,
                }
            }

        node_data = {
            "accelerator": accelerator,
            "cores": {"capacity": cores_capacity, "used": cores_used},
            "cpu": {"capacity": cpu_capacity, "used": cpu_used},
            "frequency": frequency,
            "mac_address": mac_address,
            "memory": {
                "capacity": {"rss": memory_rss_capacity, "vms": memory_vms_capacity},
                "used": {"rss": memory_rss_used, "vms": memory_vms_used},
            },
            "node_name": node_name,
            "status": status,
        }

        data["data"][node_id] = node_data

        another = click.confirm("Do you want to add another node?")
        if not another:
            break

    json_data = json.dumps(data, indent=4)
    click.echo(json_data)


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
