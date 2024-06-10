import yaml
from kubernetes import dynamic
from kubernetes.client import api_client


class ConfigMap(object):
    # """
    # Example of an api client:
    #     client = dynamic.DynamicClient(
    #         api_client.ApiClient(configuration=config.load_kube_config())
    #     )
    # """
    def __init__(self, kube_config, map_config, namespace):
        self.client = dynamic.DynamicClient(
            api_client.ApiClient(configuration=kube_config)
        )
        self.api_client = self.client.resources.get(api_version="v1", kind="ConfigMap")
        self.map_config = yaml.safe_load(open(map_config))
        self.namespace = namespace

    def create(self):
        try:
            self.configmap = self.api_client.create(
                body=self.map_config, namespace=self.namespace
            )
            print("ConfigMap created: %s" % self.configmap)
            self.name = self.configmap.metadata.name
        except Exception as e:
            print("Exception when calling configmap create: %s\n" % e)

    def get(self):
        try:
            self.configmap = self.api_client.create(
                name=self.name, namespace=self.namespace
            )
            print("ConfigMap created: %s" % self.configmap)
            return self.configmap
        except Exception as e:
            print("Exception when calling configmap create: %s\n" % e)

    def update(self, map_config):
        try:
            self.configmap = self.api_client.patch(
                body=map_config, name=self.name, namespace=self.namespace
            )
            print("Configmap created: %s" % self.configmap)
        except Exception as e:
            print("Exception when calling configmap patch: %s\n" % e)

    def delete(self):
        try:
            api_response = self.api_client.delete(
                body={}, name=self.name, namespace=self.namespace
            )
            print("Configmap created: %s" % api_response)
            self.configmap = None
        except Exception as e:
            print("Exception when calling configmap delete: %s\n" % e)
