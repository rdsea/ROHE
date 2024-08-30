import yaml
from kubernetes import dynamic
from kubernetes.client import api_client


class KubeService:
    # """
    # Example of an api client:
    #     client = dynamic.DynamicClient(
    #         api_client.ApiClient(configuration=config.load_kube_config())
    #     )
    # """
    def __init__(self, kube_config, service_config, namespace):
        self.client = dynamic.DynamicClient(
            api_client.ApiClient(configuration=kube_config)
        )
        self.api_client = self.client.resources.get(api_version="v1", kind="Service")
        self.service_config = yaml.safe_load(open(service_config))
        self.namespace = namespace

    def create(self):
        try:
            self.service = self.api_client.create(
                body=self.service_config, namespace=self.namespace
            )
            print(f"Service created: {self.service}")
            self.name = self.service.metadata.name
        except Exception as e:
            print(f"Exception when calling service create: {e}\n")

    def get(self):
        try:
            self.service = self.api_client.create(
                name=self.name, namespace=self.namespace
            )
            print(f"Service created: {self.service}")
            return self.service
        except Exception as e:
            print(f"Exception when calling service create: {e}\n")

    def update(self, service_config):
        try:
            self.service = self.api_client.patch(
                body=service_config, name=self.name, namespace=self.namespace
            )
            print(f"Service created: {self.service}")
        except Exception as e:
            print(f"Exception when calling service patch: {e}\n")

    def delete(self):
        try:
            api_response = self.api_client.delete(
                body={}, name=self.name, namespace=self.namespace
            )
            print(f"Service created: {api_response}")
            self.service = None
        except Exception as e:
            print(f"Exception when calling service delete: {e}\n")
