from typing import Callable

class ServiceRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, service_name, instance, address):
        if service_name not in self._registry:
            self._registry[service_name] = {}
        self._registry[service_name][instance] = address

    def deregister(self, service_name, instance):
        if service_name in self._registry and instance in self._registry[service_name]:
            del self._registry[service_name][instance]

    def get_service_instances(self, service_name):
        return self._registry.get(service_name, {})


# Abstract function for service discovery:
def discover_inference_instances(service_registry, criteria: Callable =None):
    inference_instances = service_registry.get_service_instances("inference")
    # filter 
    if criteria:
        inference_instances = {k: v for k, v in inference_instances.items() if criteria(k, v)}
    
    return list(inference_instances.values())

def inference_instance_selection_algo(instance, address):
    return True



if __name__ == '__main__':
    registry = ServiceRegistry()
    registry.register("inference", "instance_1", "http://192.168.1.2:5000")
    registry.register("inference", "instance_2", "http://192.168.1.3:5000")

    # Discover all inference instances.
    print(f"full list: {discover_inference_instances(registry)}")

    filter_func = lambda instance, address: "192.168.1.2" in address
    print(f"Only 192.168.1.2 host address: {discover_inference_instances(registry, criteria=filter_func)}")

    print(f"rohe framework selection algo: {discover_inference_instances(registry, inference_instance_selection_algo)}")
