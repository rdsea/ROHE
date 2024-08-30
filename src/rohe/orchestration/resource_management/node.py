from ...common.data_models import NodeData

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

"""


class Node:
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
