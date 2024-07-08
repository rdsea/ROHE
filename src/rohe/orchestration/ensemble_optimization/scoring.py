import logging
import sys
import traceback
from typing import Dict

import numpy as np
from devtools import debug

from ..resource_management.node import Node
from ..resource_management.service import Service
from ..resource_management.service_queue import ServiceQueue

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


def filtering_node(nodes: Dict[str, Node], service: Service):
    key_list = []
    for key in nodes:
        node_flag = False
        av_cpu = nodes[key].cpu.capacity - nodes[key].cpu.used
        av_mem = nodes[key].memory.capacity["rss"] - nodes[key].memory.used["rss"]
        if service.cpu <= av_cpu and service.memory["rss"] <= av_mem:
            for dev in service.accelerator:
                if service.accelerator[dev] == 0:
                    node_flag = True
                else:
                    for device in nodes[key].accelerator:
                        av_accelerator = (
                            nodes[key].accelerator[device].capacity
                            - nodes[key].accelerator[device].used
                        )
                        if (
                            nodes[key].accelerator[device].accelerator_type == dev
                            and service.accelerator[dev] < av_accelerator
                        ):
                            node_flag = True
        if node_flag:
            key_list.append(key)

    return key_list


def ranking(nodes: Dict[str, Node], keys, service: Service, weights=None):
    if weights is None:
        weights = {"cpu": 1, "memory": 1}
    node_ranks = {}
    for key in keys:
        selected_node = nodes[key]

        remain_proc = np.sort(
            np.array(selected_node.cores.capacity) - np.array(selected_node.cores.used)
        )
        req_proc = np.array(service.cores)
        req_proc.resize(remain_proc.shape)
        req_proc = np.sort(req_proc)
        remain_proc = remain_proc - req_proc
        if np.any(remain_proc < 0):
            node_ranks[key] = -1
        else:
            rank_proc = np.sum(remain_proc) / (remain_proc.size * 100)

            remain_mem = (
                selected_node.memory.capacity["rss"] - selected_node.memory.used["rss"]
            )
            rank_mem = (
                remain_mem - service.memory["rss"]
            ) / selected_node.memory.capacity["rss"]
            node_ranks[key] = weights["cpu"] * rank_proc + weights["memory"] * rank_mem

    node_ranks = {k: v for k, v in node_ranks.items() if v > 0}
    return node_ranks


def selecting_node(node_ranks, strategy=0, debug=False):
    node_id = -1
    try:
        if strategy == 0:  # first fit
            node_id = next(iter(node_ranks.keys()))
        else:
            sort_nodes = dict(sorted(node_ranks.items(), key=lambda item: item[1]))
            if strategy == 1:  # best fit
                node_id = list(sort_nodes.keys())[-1]
            elif strategy == 2:  # worst fit
                node_id = next(iter(sort_nodes.keys()))
    except Exception as e:
        if debug:
            print(f"[ERROR] - Error {type(e)} while sellecting node: {e.__traceback__}")
            traceback.print_exception(*sys.exc_info())
        else:
            logging.warning("Cannot selecting node in priorityOrchestration")
    return node_id


def assign(nodes: Dict[str, Node], node_id, service):
    if node_id in nodes:
        # debug(nodes[node_id], service)
        nodes[node_id].allocate(service)
        # print("assign success")
        logging.info(str(f"Assign {service.name} to {nodes[node_id].name}"))


def allocate_service(
    service: Service, nodes: Dict[str, Node], weights, strategy, replicas
):
    for _i in range(replicas):
        fil_nodes = filtering_node(nodes, service)
        ranking_list = ranking(nodes, fil_nodes, service, weights)
        # print(ranking_list)
        node_id = selecting_node(ranking_list, strategy)
        if node_id == -1:
            logging.warning(str(f"Cannot find node for service: {service}"))
        else:
            assign(nodes, node_id, service)


def deallocate_service(service, nodes, weights, strategy):
    pass


def orchestrate(
    nodes: Dict[str, Node],
    services: Dict[str, Service],
    service_queue: ServiceQueue,
    configuration,
):
    for key in services:
        service = services[key]
        if service.running != service.replicas:
            service_queue.put(service)

    while not service_queue.empty():
        p_service = service_queue.get()
        debug(p_service)
        if p_service is None:
            break
        replica = p_service.replicas - p_service.running
        if p_service.replicas < services[p_service.id].replicas:
            deallocate_service(
                p_service, nodes, configuration["weights"], configuration["strategy"]
            )
            continue
        allocate_service(
            p_service,
            nodes,
            configuration["weights"],
            configuration["strategy"],
            replica,
        )
