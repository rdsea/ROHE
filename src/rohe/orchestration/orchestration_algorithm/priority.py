import sys
import traceback
from typing import Dict

import numpy as np

from ...common.data_models import OrchestrateAlgorithmConfig
from ...common.logger import logger
from ..resource_management import Node, Service
from .generic_algorithm import GenericAlgorithm

FIRST_FIT = 0
BEST_FIT = 1
WORST_FIT = 2


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
        weights=None,
    ):
        if weights is None:
            weights = {"cpu": 1, "memory": 1}
        node_ranks = {}
        for key in keys:
            selected_node = nodes[key]

            remain_proc = np.sort(
                np.array(selected_node.cores.capacity)
                - np.array(selected_node.cores.used)
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
        node_id = None
        try:
            if strategy == FIRST_FIT:  # first fit
                node_id = next(iter(node_ranks.keys()))
            else:
                sort_nodes = dict(sorted(node_ranks.items(), key=lambda item: item[1]))
                if strategy == BEST_FIT:  # best fit
                    node_id = list(sort_nodes.keys())[-1]
                elif strategy == WORST_FIT:  # worst fit
                    node_id = next(iter(sort_nodes.keys()))
        except Exception as e:
            if debug:
                print(
                    f"[ERROR] - Error {type(e)} while sellecting node: {e.__traceback__}"
                )
                traceback.print_exception(*sys.exc_info())
            else:
                logger.warning("Cannot selecting node in priorityOrchestration")
        return node_id

    def find_deallocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ):
        pass

    def find_allocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ):
        fil_nodes = self.filtering_node(nodes, p_service)
        ranking_list = self.ranking(nodes, fil_nodes, p_service, config.weights)
        node_id = self.selecting_node(ranking_list, config.strategy)
        if node_id is None:
            logger.warning(str(f"Cannot find node for service: {p_service}"))
        return node_id

    def __str__(self) -> str:
        return "Priority Algorithm"
