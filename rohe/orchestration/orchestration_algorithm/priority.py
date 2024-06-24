import logging
import sys
import traceback
from typing import Dict

import numpy as np

from rohe.common.data_models import OrchestrateAlgorithmConfig
from rohe.orchestration.orchestration_algorithm.generic_algorithm import (
    GenericAlgorithm,
)

from ..resource_management import Node, Service, ServiceQueue

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class PriorityAlgorithm(GenericAlgorithm):
    def __init__(self):
        pass

    def filtering_node(self, nodes: Dict[str, Node], service: Service):
        key_list = []
        for key in nodes:
            node_flag = False
            available_cpu = nodes[key].cpu.capacity - nodes[key].cpu.used
            available_mem = (
                nodes[key].memory.capacity["rss"] - nodes[key].memory.used["rss"]
            )
            if service.cpu <= available_cpu and service.memory["rss"] <= available_mem:
                for dev in service.accelerator:
                    if service.accelerator[dev] == 0:
                        node_flag = True
                    else:
                        for device in nodes[key].accelerator:
                            available_accelerator = (
                                nodes[key].accelerator[device].capacity
                                - nodes[key].accelerator[device].used
                            )
                            if (
                                nodes[key].accelerator[device].accelerator_type == dev
                                and service.accelerator[dev] < available_accelerator
                            ):
                                node_flag = True
            if node_flag:
                key_list.append(key)

        return key_list

    def ranking(
        self,
        nodes: Dict[str, Node],
        keys,
        service: Service,
        weights={"cpu": 1, "memory": 1},
    ):
        node_ranks = {}
        for key in keys:
            selected_node = nodes[key]

            remain_proc = np.sort(
                (
                    np.array(selected_node.cores.capacity)
                    - np.array(selected_node.cores.used)
                )
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
                    selected_node.memory.capacity["rss"]
                    - selected_node.memory.used["rss"]
                )
                rank_mem = (
                    remain_mem - service.memory["rss"]
                ) / selected_node.memory.capacity["rss"]
                node_ranks[key] = (
                    weights["cpu"] * rank_proc + weights["memory"] * rank_mem
                )

        node_ranks = {k: v for k, v in node_ranks.items() if v > 0}
        return node_ranks

    def selecting_node(self, node_ranks, strategy=0, debug=False):
        node_id = -1
        try:
            if strategy == 0:  # first fit
                node_id = list(node_ranks.keys())[0]
            else:
                sort_nodes = dict(sorted(node_ranks.items(), key=lambda item: item[1]))
                if strategy == 1:  # best fit
                    node_id = list(sort_nodes.keys())[-1]
                elif strategy == 2:  # worst fit
                    node_id = list(sort_nodes.keys())[0]
        except Exception as e:
            if debug:
                print(
                    "[ERROR] - Error {} while sellecting node: {}".format(
                        type(e), e.__traceback__
                    )
                )
                traceback.print_exception(*sys.exc_info())
            else:
                logging.warning("Cannot selecting node in priorityOrchestration")
        return node_id

    def assign(self, nodes: Dict[str, Node], node_id, service):
        if node_id in nodes:
            # debug(nodes[node_id], service)
            nodes[node_id].allocate(service)
            # print("assign success")
            logging.info(
                str("Assign {} to {}".format(service.name, nodes[node_id].name))
            )

    def allocate_service(
        self, service: Service, nodes: Dict[str, Node], weights, strategy, replicas
    ):
        for _ in range(replicas):
            fil_nodes = self.filtering_node(nodes, service)
            ranking_list = self.ranking(nodes, fil_nodes, service, weights)
            # print(ranking_list)
            node_id = self.selecting_node(ranking_list, strategy)
            if node_id == -1:
                logging.warning(str("Cannot find node for service: {}".format(service)))
            else:
                self.assign(nodes, node_id, service)

    def deallocate_service(self, service, nodes, weights, strategy):
        pass

    def calculate(
        self,
        nodes: Dict[str, Node],
        services: Dict[str, Service],
        service_queue: ServiceQueue,
        config: OrchestrateAlgorithmConfig,
    ):
        while not service_queue.empty():
            p_service = service_queue.get()
            if p_service is None:
                break
            replica = p_service.replicas - p_service.running
            if p_service.replicas < services[p_service.id].replicas:
                self.deallocate_service(
                    p_service,
                    nodes,
                    config.weights,
                    config.strategy,
                )
                continue
            self.allocate_service(
                p_service,
                nodes,
                config.weights,
                config.strategy,
                replica,
            )

    def __str__(self) -> str:
        return "Priority Algorithm"
