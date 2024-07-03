import json
import logging
import random
import uuid

import requests

headers = {"Content-Type": "application/json"}


class ConsulClient:
    def __init__(self, config) -> None:
        """
        Example config:
        config = {
            "url": "http://127.0.0.1:8500",
            "token": None,
            "datacenter": None,
            "adapter": None
        }
        """
        if "url" in config:
            self.url = config["url"]
        else:
            self.url = "http://localhost:8500"
            logging.debug("Consul ULR is not set! Using default localhost")
        self.registerLink = self.url + "/v1/agent/service/register"
        self.deregisterLink = self.url + "/v1/agent/service/deregister/"
        self.getServiceLink = self.url + "/v1/catalog/services"

    def service_register(
        self,
        name: str,
        id: str = "",
        tag: list | None = None,
        address: str = "",
        metadata: dict | None = None,
        port: int = 0,
        kind: str = "",
        check=None,
        checks=None,
        enable_tag_override: bool = False,
        weight=None,
    ):
        service_conf = {"Name": name}

        if id == "":
            id = str(uuid.uuid4())
        if address != "":
            service_conf["Address"] = address
        if metadata is not None:
            service_conf["Meta"] = metadata
        if kind != "":
            service_conf["Kind"] = kind
        if tag is not None:
            service_conf["Tags"] = tag

        service_conf["ID"] = id
        service_conf["Port"] = port
        service_conf["EnableTagOverride"] = enable_tag_override

        response = requests.put(
            url=self.registerLink, headers=headers, data=json.dumps(service_conf)
        )

        if response.status_code == 200:
            return id
        else:
            logging.error(f"Unable to register for service {name}")
            return None

    def service_deregister(self, id):
        response = requests.put(url=self.deregisterLink + str(id))
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Unable to register for service {id}")
            return False

    def query_service(self, name: str, tags: list | None = None):
        service_url = self.url + "/v1/catalog/service/" + name
        params = {}
        if tags:
            params["tag"] = tags

        response = requests.get(service_url, headers=headers, params=params)
        if response.status_code == 200:
            services_info = response.json()
            # print(f"This is service info: {services_info}, type: {type(services_info)}")

            services = []
            for service in services_info:
                if isinstance(service, dict):
                    service_dict = {
                        "ID": service.get("ServiceID", ""),
                        "Address": service.get("ServiceAddress", ""),
                        "Port": service.get("ServicePort", ""),
                        "Tags": service.get("ServiceTags", []),
                        "Metadata": service.get("ServiceMeta", {}),
                    }
                    services.append(service_dict)
            return services
        else:
            logging.error(
                f"Failed to query services. Status code: {response.status_code}. Response: {response.text}"
            )
            return []

    def get_all_service_instances(self, name: str, tags: list | None = None):
        """
        Get all service instances based on name and tags.
        """
        services = self.query_service(name, tags)
        return services

    def get_n_random_service_instances(
        self, name: str, tags: list | None = None, n: int = 3
    ):
        """
        Get N random service instances based on name and tags.
        """
        services = self.query_service(name, tags)
        if n >= len(services):
            return services
        return random.sample(services, n)

    def get_quorum_service_instances(self, name: str, tags: list | None = None):
        """
        Get a quorum (majority) of service instances, randomly selected, based on name and tags.
        """
        services = self.query_service(name, tags)
        quorum = (len(services) // 2) + 1
        return self.get_n_random_service_instances(name, tags, quorum)

    # def retrieve_inference_service_address(self, service_info: list):


"""
# Example code
# Document: https://developer.hashicorp.com/consul/api-docs/catalog#list-services

import os, sys
ROHE_PATH = os.getenv('ROHE_PATH')
sys.path.append(ROHE_PATH)

consul_conf = {
    "url": "http://localhost:8500"
}

from lib.serviceRegistry.consul import ConsulClient

client = consulClient(consul_conf)

service_id = client.serviceRegister("mongo", tag=["test", "demo1"])
if service_id != None:
    print(service_id, ": Registered")

response = client.serviceDeregister(service_id)
if response:
    print(service_id, ": Deregistered")

"""
