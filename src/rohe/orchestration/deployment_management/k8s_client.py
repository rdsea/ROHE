import datetime

import pytz
from devtools import debug
from kubernetes.client.rest import ApiException

from ...external.k8s.datamodel.api.apps.v1 import Deployment, DeploymentSpec
from ...external.k8s.datamodel.api.core.v1 import (
    Container,
    ContainerPort,
    EnvVar,
    EnvVarSource,
    ObjectFieldSelector,
    PodSpec,
    PodTemplateSpec,
)
from ...external.k8s.datamodel.apimachinery.pkg.apis.meta.v1 import (
    LabelSelector,
    ObjectMeta,
)
from ..resource_management import ServiceInstance


class K8sClient:
    def __init__(
        self,
        # deploy_config, namespace, api_client
    ):
        pass
        # self.deploy_config = yaml.safe_load(open(deploy_config))
        # self.namespace = namespace
        # self.name = self.deploy_config["metadata"]["name"]
        # self.api_client = api_client
        # self.deployment = None
        # self.client_v1 = client.CoreV1Api()

    def create(self):
        try:
            api_response = self.client_v1.create_namespaced_deployment(
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
            api_response = self.client_v1.delete_namespaced_deployment(
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
            api_response = self.client_v1.patch_namespaced_deployment(
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
            api_response = self.client_v1.read_namespaced_deployment(
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
            api_response = self.client_v1.replace_namespaced_deployment(
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
            api_response = self.client_v1.patch_namespaced_deployment(
                name=self.name, namespace=self.namespace, body=self.deployment
            )
            print("Deployment updated: \n%s" % api_response)
        except ApiException as e:
            print(
                "Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n"
                % e
            )

    def generate_deployment(self, service_instance: ServiceInstance):
        task_name = service_instance.service.name
        node_name = service_instance.node.name
        test = Deployment(
            apiVersion="apps/v1",
            kind="Deployment",
            metadata=ObjectMeta(
                name=f"{task_name}-{service_instance.node.name}",
                labels={"app": task_name},
            ),
            spec=DeploymentSpec(
                replicas=1,
                selector=LabelSelector(matchLabels={"app": task_name}),
                template=PodTemplateSpec(
                    metadata=ObjectMeta(labels={"app": task_name}),
                    spec=PodSpec(
                        restartPolicy="Always",
                        nodeSelector={"kubernetes.io/hostname": node_name},
                        containers=[
                            Container(
                                name=task_name,
                                image=service_instance.service.image,
                                imagePullPolicy="Always",
                                ports=[
                                    ContainerPort(containerPort=port)
                                    for port in service_instance.service.ports
                                ],
                                env=[
                                    EnvVar(
                                        name="NODE_NAME",
                                        valueFrom=EnvVarSource(
                                            fieldRef=ObjectFieldSelector(
                                                fieldPath="spec.nodeName"
                                            )
                                        ),
                                    ),
                                    EnvVar(
                                        name="POD_ID",
                                        valueFrom=EnvVarSource(
                                            fieldRef=ObjectFieldSelector(
                                                fieldPath="metadata.name"
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ],
                    ),
                ),
            ),
        )
        debug(test.model_dump(exclude_defaults=True))
