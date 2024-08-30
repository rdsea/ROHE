import json


class TaskOrc:
    def __init__(self, configuration, pre_task, next_task):
        self.name = configuration["name"]
        self.resource_avg = configuration["resource_avg"]
        self.resource_max = configuration["resource_max"]
        self.deployment = configuration["deployment"]
        # node_list - list of dictionary: {node_name: num_replicas}
        self.node_list = []
        self.priority = configuration["priority"]

        self.pre_task = pre_task
        self.next_task = next_task
        task_config = json.load(open(configuration))
        self.id = task_config["id"]
        self.lable = task_config["lable"]
        self.catetory = {}
        self.replicas = task_config["replicas"]
        self.deployment = configuration["deployment"]
        self.image = task_config["image"]
        self.requirement = task_config["requirement"]
        self.status = 0
        self.queue_capacity = task_config["queue_cap"]
        self.n_queue = 0  # current number of requests in waiting queue

    def assign(self, node_name):
        if node_name in self.node_list:
            self.node_list[node_name] += 1
        else:
            self.node_list[node_name] = 1

    def run(self):
        # To Do
        # Send kubectl apply deployment
        pass

    def scale(self, n_rep):
        # To Do
        # Send kubectl scale --replicas=n_rep
        pass

    def stop(self):
        # To Do
        # Send scale deployment to 0 replicas
        self.scale(0)

    def restart(self):
        # To Do
        # Restart the task
        self.stop()
        self.scale(self.replicas)

    def update(self):
        # To Do
        # Update task status, n_queue, current resource usage, replicas.
        pass
