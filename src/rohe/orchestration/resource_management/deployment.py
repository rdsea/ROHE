import datetime

import kubernetes.client
import pytz
import yaml
from kubernetes.client.rest import ApiException


class Deployment:
    def __init__(self, deploy_config, namespace, api_client):
        self.deploy_config = yaml.safe_load(open(deploy_config))
        self.namespace = namespace
        self.name = self.deploy_config["metadata"]["name"]
        self.api_client = api_client
        self.deployment = None
        self.api_instance = kubernetes.client.AppsV1Api(self.api_client)

    def create(self):
        try:
            api_response = self.api_instance.create_namespaced_deployment(
                body=self.deploy_config, namespace=self.namespace
            )
            self.deployment = api_response
            print(f"Deployment created: {self.name}")
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->create_namespaced_deployment: {e}\n"
            )

    def delete(self):
        try:
            api_response = self.api_instance.delete_namespaced_deployment(
                name=self.name, namespace=self.namespace
            )
            print(f"Deployment deleted: \n{api_response.status}")
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->delete_namespaced_deployment: {e}\n"
            )

    def update(self, deploy_config):
        try:
            api_response = self.api_instance.patch_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=deploy_config
            )
            print(f"Deployment updated: \n{api_response}")
            self.deploy_config = deploy_config
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->patch_namespaced_deployment: {e}\n"
            )

    def get_info(self):
        try:
            api_response = self.api_instance.read_namespaced_deployment(
                name=self.name, namespace=self.namespace
            )
            print(f"Deployment deleted: \n{api_response}")
            return api_response
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->delete_namespaced_deployment: {e}\n"
            )

    def replace(self, deploy_config):
        try:
            api_response = self.api_instance.replace_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=deploy_config
            )
            print(f"Deployment updated: \n{api_response}")
            self.deploy_config = deploy_config
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->replace_namespaced_deployment: {e}\n"
            )

    def restart(self):
        self.deployment = self.get_info()
        self.deployment.spec.template.metadata.annotations = {
            "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow()
            .replace(tzinfo=pytz.UTC)
            .isoformat()
        }
        try:
            api_response = self.api_instance.patch_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=self.deployment
            )
            print(f"Deployment updated: \n{api_response}")
        except ApiException as e:
            print(
                f"Exception when calling AppsV1Api->patch_namespaced_deployment: {e}\n"
            )
