class Node(object):
    def __init__(self, config):
        # configuration - dictionary, including: 
        # node_name - string 
        # address (ip) - string 
        # cpu - integer
        # mem - integer
        # accelerator - string  
        self.name = config["node_name"]
        self.accelerator = config["accelerator"]
        self.available_cpu = self.config["cpu"]
        self.available_mem = self.config["mem"]
        # service_list - list of dictionary: {service_name: num_replicas}
        self.service_list = []
        self.max_processes = 4*self.config["cpu"]/1000
        self.available_proc = self.max_processes
    
    def set_max_processes(self, num_processes):
        self.max_processes = num_processes

    def get_resource_av(self):
        return {"cpu": self.available_cpu, 
                "mem": self.available_mem, 
                "proc": self.available_proc}
    def get_resource(self):
        return {"cpu": self.config["cpu"], 
                "mem": self.config["mem"], 
                "proc": self.max_processes}

    def assign(self, task):
        if ((task.resource_avg["cpu"] > self.available_cpu) or (task.resource_avg["mem"] > self.available_mem) or (task.resource_avg["proc"] > self.available_proc)):
            return False
        else:
            if "accelerator" in task.resource_avg:
                if not (self.accelerator == task.resource_avg["accelerator"]):
                    return False
            self.available_cpu  = self.available_cpu - task.resource_avg["cpu"]
            self.available_mem  = self.available_mem - task.resource_avg["mem"]
            self.available_proc  = self.available_proc - task.resource_avg["proc"]
            task.assign(self.name)
            if task.name in self.service_list:
                self.service_list[task.name] += 1
            else:
                self.service_list[task.name] = 1
            return True





