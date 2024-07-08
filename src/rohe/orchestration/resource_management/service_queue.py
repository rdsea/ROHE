from queue import PriorityQueue
from typing import Tuple

from ...common.data_models import ServiceQueueConfig
from ...common.rohe_enum import SensitivityEnum
from .service import Service


class ServiceQueue:
    def __init__(self, config: ServiceQueueConfig):
        self.config = config
        # Priority:
        # 0 - No Priority; 1 - CPU sensitive priority; 2 - Memory sensitive priority
        self.priority_factor = config.priority
        self.queue_balance = config.queue_balance
        self.priority_count = 0
        self.p_queue = PriorityQueue[Tuple[int, Service]]()
        self.np_queue = PriorityQueue[Tuple[int, Service]]()
        self.update_flag = False

    def empty(self):
        return self.p_queue.empty() and self.np_queue.empty()

    def put(self, service: Service):
        if (self.priority_factor > 0) and (
            service.sensitivity in (self.priority_factor, 3)
        ):
            service.set_qtime()
            if self.priority_factor <= SensitivityEnum.cpu_sensitive:
                self.p_queue.put((-service.cpu, service))
            elif self.priority_factor == SensitivityEnum.memory_sensitive:
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
