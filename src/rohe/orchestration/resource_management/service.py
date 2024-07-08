from __future__ import annotations

import time
import uuid

from ...common.data_models import ServiceData

# from ..deployment_management.kube_generator import kube_generator

"""
Service config:
{
    "service_name":"object_detection_service",
    "cpu": 500,
    "accelerator": {
        "gpu": 12
    },
    "memory": {
        "rss": 200,
        "vms": 200
    },
    "cores": 1,
    "sensitivity": 0,
    "replicas": 1
}
"""

EPSILON = 1e-9


class ServiceInstance:
    def __init__(self, service: Service, node):
        self.node = node
        self.service = service
        self.id = str(uuid.uuid4())
        self.gen_deployment = False

    def generate_deployment(self):
        if not self.gen_deployment:
            # kube_generator(self)
            self.gen_deployment = True

    def __str__(self):
        instance_info = (
            "Service Name: "
            + str(self.service.name)
            + "\nID: "
            + str(self.id)
            + "\n Node Name: \n"
            + str(self.node.name)
        )
        return instance_info

    def __repr__(self):
        instance_info = (
            "Service Name: "
            + str(self.service.name)
            + "\nID: "
            + str(self.id)
            + "\n Node Name: \n"
            + str(self.node.name)
        )
        return instance_info


class Service:
    def __init__(self, config: ServiceData):
        self.q_time = time.time()
        self.update(config)
        self.instances: dict[str, ServiceInstance] = {}
        self.queueing = self.replicas

    def update(self, config: ServiceData):
        self.config = config
        self.name = self.config.service_name
        self.cpu = self.config.cpu_required
        self.memory = self.config.memory_required
        self.cores = self.config.cores_required
        self.accelerator = self.config.accelerator_required
        self.sensitivity = self.config.sensitivity
        # Sensitivity:
        # 0 - Not sensitive; 1 - CPU sensitive; 2 - Memory sensitive; 3 CPU & Memory sensitive
        self.replicas = self.config.replicas
        self.image = self.config.image
        self.ports = self.config.ports
        self.port_mapping = self.config.port_mapping
        self.node_list = self.config.node
        self.id = self.config.service_id
        self.status = self.config.status
        self.running = self.config.running
        self.instance_ids = self.config.instance_ids

    def get_running_count(self):
        self.running = len(self.instance_ids)
        return self.running

    def get_queueing_count(self):
        self.queueing = self.replicas - len(self.instance_ids)
        return self.queueing

    def self_update_config(self):
        self.config.node = self.node_list
        self.config.running = self.running
        self.config.instance_ids = self.instance_ids

    def set_replicas(self, rep: int):
        self.replicas = rep

    def set_qtime(self):
        self.q_time = time.time()

    def __lt__(self, other: Service):
        return self.q_time < other.q_time

    def __gt__(self, other: Service):
        return self.q_time > other.q_time

    def __le__(self, other: Service):
        return self.q_time <= other.q_time

    def __ge__(self, other: Service):
        return self.q_time >= other.q_time

    def __eq__(self, other):
        return (self.q_time - other.q_time) < EPSILON

    def __str__(self):
        service_info = (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\n Nodes: \n"
            + str(self.node_list)
        )
        return service_info

    def __repr__(self):
        service_info = (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\n Nodes: \n"
            + str(self.node_list)
        )
        return service_info
