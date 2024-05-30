import datetime

import kubernetes.client
import pytz
import yaml
from kubernetes.client.rest import ApiException


class Deployment(object):
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
            print("Deployment created: %s" % self.name)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->create_namespaced_deployment: %s\n"
                % e
            )

    def delete(self):
        try:
            api_response = self.api_instance.delete_namespaced_deployment(
                name=self.name, namespace=self.namespace
            )
            print("Deployment deleted: \n%s" % api_response.status)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->delete_namespaced_deployment: %s\n"
                % e
            )

    def update(self, deploy_config):
        try:
            api_response = self.api_instance.patch_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=deploy_config
            )
            print("Deployment updated: \n%s" % api_response)
            self.deploy_config = deploy_config
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n"
                % e
            )

    def get_info(self):
        try:
            api_response = self.api_instance.read_namespaced_deployment(
                name=self.name, namespace=self.namespace
            )
            print("Deployment deleted: \n%s" % api_response)
            return api_response
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->delete_namespaced_deployment: %s\n"
                % e
            )

    def replace(self, deploy_config):
        try:
            api_response = self.api_instance.replace_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=deploy_config
            )
            print("Deployment updated: \n%s" % api_response)
            self.deploy_config = deploy_config
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->replace_namespaced_deployment: %s\n"
                % e
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
            print("Deployment updated: \n%s" % api_response)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n"
                % e
            )
