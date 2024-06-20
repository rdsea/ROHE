import numpy as np

from .node import Node
from .service import Service, ServiceInstance


class Allocator:
    def __init__(self) -> None:
        pass

    def assign(self, node: Node, service: Service):
        if node.id in service.node_list:
            service.node_list[node.id] += 1
        else:
            service.node_list[node.id] = 1
        new_instance = ServiceInstance(service, node)
        service.instances[new_instance.id] = new_instance
        service.instance_ids = list(service.instances.keys())
        service.running = len(service.instance_ids)
        service.self_update_config()
        new_instance.generate_deployment()

    def allocate(self, node: Node, service: Service):
        node.cpu.used = node.cpu.used + service.cpu
        node.memory.used["rss"] += service.memory["rss"]
        node.memory.used["vms"] += service.memory["vms"]
        for dev in service.accelerator:
            for device in node.accelerator:
                av_accelerator = (
                    node.accelerator[device].capacity - node.accelerator[device].used
                )
                if (
                    node.accelerator[device].accelerator_type == dev
                    and service.accelerator[dev] < av_accelerator
                ):
                    node.accelerator[device].used = (
                        node.accelerator[device].used + service.accelerator[dev]
                    )
        used_proc = np.sort(np.array(node.cores.used))
        req_proc = np.array(service.cores)
        req_proc.resize(used_proc.shape)
        self.assign(node, service)
        req_proc = -np.sort(-req_proc)
        used_proc = used_proc + req_proc
        node.cores.used = used_proc.tolist()
        if service.id in node.service_list:
            node.service_list[service.id] += 1
        else:
            node.service_list[service.id] = 1
        node.self_update()
