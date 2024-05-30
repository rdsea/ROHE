import time
import uuid
from queue import PriorityQueue

import numpy as np

# import sys
# main_path = config_file = qoaUtils.get_parent_dir(__file__,2)
# sys.path.append(main_path)
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
    "processor": {
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
    "processor": 1,
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

    def generateDeployment(self):
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
    def __init__(self, config):
        self.q_time = time.time()
        self.update(config)
        self.instances = {}
        self.queueing = self.replicas

    def update(self, config):
        self.config = config
        self.name = self.config["service_name"]
        self.cpu = self.config["cpu"]
        self.memory = self.config["memory"]
        self.processor = self.config["processor"]
        self.accelerator = self.config["accelerator"]
        self.sensitivity = self.config["sensitivity"]
        # Sensitivity:
        # 0 - Not sensitive; 1 - CPU sensitive; 2 - Memory sensitve; 3 CPU & Memory sensitive
        self.replicas = self.config["replicas"]
        self.image = self.config["image"]
        self.ports = self.config["ports"]
        self.port_mapping = self.config["port_mapping"]
        self.node_list = self.config["node"]
        self.id = self.config["service_id"]
        self.status = self.config["status"]
        self.running = self.config["running"]
        self.instance_ids = self.config["instance_ids"]

    def getRunningCount(self):
        self.running = len(self.instance_ids)
        return self.running

    def getQueueingCount(self):
        self.queueing = self.replicas - len(self.instance_ids)
        return self.queueing

    def selfUpdateConfig(self):
        self.config["node"] = self.node_list
        self.config["running"] = self.running
        self.config["instance_ids"] = self.instance_ids

    def assign(self, node):
        if node.id in self.node_list:
            self.node_list[node.id] += 1
        else:
            self.node_list[node.id] = 1
        new_instance = ServiceInstance(self, node)
        self.instances[new_instance.id] = new_instance
        self.instance_ids = list(self.instances.keys())
        self.running = len(self.instance_ids)
        self.selfUpdateConfig()
        new_instance.generateDeployment()

    def set_replicas(self, rep):
        self.replicas = rep

    def set_qtime(self):
        self.q_time = time.time()

    def __lt__(self, other):
        return self.q_time < other.q_time

    def __gt__(self, other):
        return self.q_time > other.q_time

    def __le__(self, other):
        return self.q_time <= other.q_time

    def __ge__(self, other):
        return self.q_time >= other.q_time

    def __eq__(self, other):
        return self.q_time == other.q_time

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
        self.p_queue = PriorityQueue()
        self.np_queue = PriorityQueue()
        self.update_flag = False

    def empty(self):
        return self.p_queue.empty() and self.np_queue.empty()

    def put(self, service):
        if (self.priority_factor > 0) and (
            (service.sensitivity == self.priority_factor) or (service.sensitivity == 3)
        ):
            service.set_qtime(time.time())
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
    def __init__(self, config):
        # configuration - dictionary, including:
        # node_name - string
        # address (ip) - string
        # cpu - integer
        # mem - integer
        # accelerator - string
        self.update(config)

    def update(self, config):
        self.config = config
        if "service" not in config:
            self.config["service"] = {}
        self.mac = self.config["MAC"]
        self.id = self.mac
        self.name = self.config["node_name"]
        self.status = self.config["status"]
        self.frequency = self.config["frequency"]
        self.accelerator = self.config["accelerator"]
        self.cpu = self.config["cpu"]
        self.memory = self.config["memory"]
        self.processor = self.config["processor"]
        # service_list - list of dictionary: {service_name: num_replicas}
        self.service_list = self.config["service"]

    def set_max_processes(self, num_processes):
        self.processor["capacity"] = num_processes

    def get_resource_av(self):
        return {
            "cpu": self.cpu["capacity"] - self.cpu["used"],
            "mem": {
                "rss": self.memory["capacity"]["rss"] - self.memory["used"]["rss"],
                "vms": self.memory["capacity"]["vms"] - self.memory["used"]["vms"],
            },
            "proc": self.processor["capacity"] - self.processor["used"],
        }

    def get_resource(self):
        return {
            "cpu": self.cpu["capacity"],
            "mem": {
                "rss": self.memory["capacity"]["rss"],
                "vms": self.memory["capacity"]["vms"],
            },
            "proc": self.processor["capacity"],
        }

    def allocate(self, service):
        self.cpu["used"] = self.cpu["used"] + service.cpu
        self.memory["used"]["rss"] = self.memory["used"]["rss"] + service.memory["rss"]
        self.memory["used"]["vms"] = self.memory["used"]["vms"] + service.memory["vms"]
        for dev in service.accelerator:
            for device in self.accelerator:
                av_accelerator = (
                    self.accelerator[device]["capacity"]
                    - self.accelerator[device]["used"]
                )
                if (
                    self.accelerator[device]["type"] == dev
                    and service.accelerator[dev] < av_accelerator
                ):
                    self.accelerator[device]["used"] = (
                        self.accelerator[device]["used"] + service.accelerator[dev]
                    )
        used_proc = np.sort(np.array(self.processor["used"]))
        req_proc = np.array(service.processor)
        req_proc.resize(used_proc.shape)
        service.assign(self)
        req_proc = -np.sort(-req_proc)
        used_proc = used_proc + req_proc
        self.processor["used"] = used_proc.tolist()
        if service.id in self.service_list:
            self.service_list[service.id] += 1
        else:
            self.service_list[service.id] = 1
        self.selfUpdate()

    def selfUpdate(self):
        self.config["cpu"] = self.cpu
        self.config["memory"] = self.memory
        self.config["processor"] = self.processor
        self.config["accelerator"] = self.accelerator
        self.config["service"] = self.service_list

    def __str__(self):
        node_info = (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\nResource: \n CPU: \n  Capacity: "
            + str(self.cpu["capacity"])
            + "\n  Used: "
            + str(self.cpu["used"])
            + "\n Memory: \n  Capacity: "
            + str(self.memory["capacity"]["rss"])
            + "\n  Used: "
            + str(self.memory["used"]["rss"])
            + "\n Accelerator: \n"
            + str(self.accelerator)
            + "\n Services: \n"
            + str(self.service_list)
            + "\n Processor: \n  Capacity: "
            + str(self.processor["capacity"])
            + "\n  Used: "
            + str(self.processor["used"])
            + "\n"
        )
        return node_info

    def __repr__(self):
        node_info = (
            "Name: "
            + self.name
            + "\nID: "
            + self.id
            + "\nResource: \n CPU: \n  Capacity: "
            + str(self.cpu["capacity"])
            + "\n  Used: "
            + str(self.cpu["used"])
            + "\n Memory: \n  Capacity: "
            + str(self.memory["capacity"]["rss"])
            + "\n  Used: "
            + str(self.memory["used"]["rss"])
            + "\n Accelerator: \n"
            + str(self.accelerator)
            + "\n Services: \n"
            + str(self.service_list)
            + "\n Processor: \n  Capacity: "
            + str(self.processor["capacity"])
            + "\n  Used: "
            + str(self.processor["used"])
            + "\n"
        )
        return node_info


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
