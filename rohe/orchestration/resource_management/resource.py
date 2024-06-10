from __future__ import annotations

import time
import uuid
from queue import PriorityQueue
from typing import Dict, Tuple

import numpy as np

from ...common.data_models import NodeData, ServiceData
from ..deployment_management.kube_generator import kube_generator

"""
Node config:
{
    "node_name":"RaspberryPi_01",
    "frequency": 1.5,
    "accelerator":{
        "GPU0":{
            "mode": "pre-emptive",
            "core": 512,
            "capacity": 100
        }
    },
    "cpu": {
        "capacity": 4000
    },
    "memory": {
        "capacity": {
            "rss": 4096,
            "vms": 2048
        }
    },
    "cores": {
        "capacity": 4
    }
}

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


class ServiceInstance(object):
    def __init__(self, service, node):
        self.node = node
        self.service = service
        self.id = str(uuid.uuid4())
        self.gen_deployment = False

    def generate_deployment(self):
        if not self.gen_deployment:
            kube_generator(self)
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


class Service(object):
    def __init__(self, config: ServiceData):
        self.q_time = time.time()
        self.update(config)
        self.instances: Dict[str, ServiceInstance] = {}
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
        # 0 - Not sensitive; 1 - CPU sensitive; 2 - Memory sensitve; 3 CPU & Memory sensitive
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

    def assign(self, node: Node):
        if node.id in self.node_list:
            self.node_list[node.id] += 1
        else:
            self.node_list[node.id] = 1
        new_instance = ServiceInstance(self, node)
        self.instances[new_instance.id] = new_instance
        self.instance_ids = list(self.instances.keys())
        self.running = len(self.instance_ids)
        self.self_update_config()
        new_instance.generate_deployment()

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
        return (self.q_time - other.q_time) < 1e-9

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


class ServiceQueue(object):
    def __init__(self, config):
        self.config = config
        # Priority:
        # 0 - No Priority; 1 - CPU sensitive priority; 2 - Memory sensitve priority
        self.priority_factor = config["priority"]
        self.queue_balance = config["queue_balance"]
        self.priority_count = 0
        self.p_queue = PriorityQueue[Tuple[int, Service]]()
        self.np_queue = PriorityQueue[Tuple[int, Service]]()
        self.update_flag = False

    def empty(self):
        return self.p_queue.empty() and self.np_queue.empty()

    def put(self, service: Service):
        if (self.priority_factor > 0) and (
            (service.sensitivity == self.priority_factor) or (service.sensitivity == 3)
        ):
            service.set_qtime()
            if self.priority_factor <= 1:
                self.p_queue.put((-service.cpu, service))
            elif self.priority_factor == 2:
                self.p_queue.put((-service.memory["rss"], service))
        else:
            self.np_queue.put((-service.cpu, service))

    def get(self):
        if not self.p_queue.empty() and self.priority_count > self.queue_balance:
            self.priority_count += 1
            return self.p_queue.get()[1]
        elif not self.np_queue.empty():
            self.priority_count = 0
            return self.np_queue.get()[1]
        else:
            return None


class Node(object):
    def __init__(self, config: NodeData):
        # configuration - dictionary, including:
        # node_name - string
        # address (ip) - string
        # cpu - integer
        # mem - integer
        # accelerator - string
        self.update(config)

    def update(self, config: NodeData):
        self.config = config
        if self.config.services is None:
            self.config.services = {}
        self.mac_address = self.config.mac_address
        self.id = self.mac_address
        self.name = self.config.node_name
        self.status = self.config.status
        self.frequency = self.config.frequency
        self.accelerator = self.config.accelerator
        self.cpu = self.config.cpu
        self.memory = self.config.memory
        self.cores = self.config.cores
        # service_list - list of dictionary: {service_name: num_replicas}
        self.service_list = self.config.services

    def set_max_processes(self, num_processes):
        self.cores.capacity = num_processes

    def get_resource_av(self):
        return {
            "cpu": self.cpu.capacity - self.cpu.used,
            "memory": {
                "rss": self.memory.capacity["rss"] - self.memory.used["rss"],
                "vms": self.memory.capacity["vms"] - self.memory.used["vms"],
            },
            "cores": [a - b for a, b in zip(self.cores.capacity, self.cores.used)],
        }

    def get_resource(self):
        return {
            "cpu": self.cpu.capacity,
            "memory": {
                "rss": self.memory.capacity["rss"],
                "vms": self.memory.capacity["vms"],
            },
            "cores": self.cores.capacity,
        }

    def allocate(self, service):
        self.cpu.used = self.cpu.used + service.cpu
        self.memory.used["rss"] += service.memory["rss"]
        self.memory.used["vms"] += service.memory["vms"]
        for dev in service.accelerator:
            for device in self.accelerator:
                av_accelerator = (
                    self.accelerator[device].capacity - self.accelerator[device].used
                )
                if (
                    self.accelerator[device].accelerator_type == dev
                    and service.accelerator[dev] < av_accelerator
                ):
                    self.accelerator[device].used = (
                        self.accelerator[device].used + service.accelerator[dev]
                    )
        used_proc = np.sort(np.array(self.cores.used))
        req_proc = np.array(service.cores)
        req_proc.resize(used_proc.shape)
        service.assign(self)
        req_proc = -np.sort(-req_proc)
        used_proc = used_proc + req_proc
        self.cores.used = used_proc.tolist()
        if service.id in self.service_list:
            self.service_list[service.id] += 1
        else:
            self.service_list[service.id] = 1
        self.self_update()

    def self_update(self):
        self.config.cpu = self.cpu
        self.config.memory = self.memory
        self.config.cores = self.cores
        self.config.accelerator = self.accelerator
        self.config.services = self.service_list

    def __str__(self):
        return (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\nResource: \n CPU: \n  Capacity: "
            + str(self.cpu.capacity)
            + "\n  Used: "
            + str(self.cpu.used)
            + "\n Memory: \n  Capacity: "
            + str(self.memory.capacity["rss"])
            + "\n  Used: "
            + str(self.memory.used["rss"])
            + "\n Accelerator: \n"
            + str(self.accelerator)
            + "\n Services: \n"
            + str(self.service_list)
            + "\n Cores: \n  Capacity: "
            + str(self.cores.capacity)
            + "\n  Used: "
            + str(self.cores.used)
            + "\n"
        )

    def __repr__(self):
        return (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\nResource: \n CPU: \n  Capacity: "
            + str(self.cpu.capacity)
            + "\n  Used: "
            + str(self.cpu.used)
            + "\n Memory: \n  Capacity: "
            + str(self.memory.capacity["rss"])
            + "\n  Used: "
            + str(self.memory.used["rss"])
            + "\n Accelerator: \n"
            + str(self.accelerator)
            + "\n Services: \n"
            + str(self.service_list)
            + "\n Cores: \n  Capacity: "
            + str(self.cores.capacity)
            + "\n  Used: "
            + str(self.cores.used)
            + "\n"
        )


class NodeCollection(object):
    def __init__(self, nodes=None):
        if nodes is None:
            self.collection = {}
        else:
            self.collection = nodes

    def add(self, node):
        self.collection[node.id] = node

    def remove(self, node_name):
        return self.collection.pop(node_name)

    def __str__(self):
        collection_info = ""
        for key in self.collection:
            collection_info = collection_info + str(self.collection[key]) + "\n"
        return collection_info

    def __repr__(self):
        collection_info = ""
        for key in self.collection:
            collection_info = collection_info + str(self.collection[key]) + "\n"
        return collection_info
