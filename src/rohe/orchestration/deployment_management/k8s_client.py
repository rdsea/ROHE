from pathlib import Path

import yaml
from kubernetes import client, config, utils

from ...external.k8s.datamodel.api.apps.v1 import Deployment, DeploymentSpec
from ...external.k8s.datamodel.api.core.v1 import (
    Container,
    ContainerPort,
    EnvVar,
    EnvVarSource,
    ObjectFieldSelector,
    PodSpec,
    PodTemplateSpec,
    Service,
    ServicePort,
    ServiceSpec,
)
from ...external.k8s.datamodel.apimachinery.pkg.apis.meta.v1 import (
    LabelSelector,
    ObjectMeta,
)
from ...variable import ROHE_PATH
from ..resource_management import ServiceInstance


class K8sClient:
    def __init__(self):
        config.load_kube_config()
        self.client = client.ApiClient()

        Path(f"{ROHE_PATH}/temp/k8s_deployment").mkdir(parents=True, exist_ok=True)

    def generate_deployment(self, service_instance: ServiceInstance):
        task_name = service_instance.service.name
        node_name = service_instance.node.name
        deployment = Deployment(
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
        return deployment.model_dump(exclude_defaults=True)

    def generate_service(self, service_instance: ServiceInstance):
        task_name = service_instance.service.name
        service = Service(
            apiVersion="v1",
            kind="Service",
            metadata=ObjectMeta(
                name=f"{task_name}-service",
            ),
            spec=ServiceSpec(
                ports=[
                    ServicePort(port=p_map.con_port, targetPort=p_map.phy_port)
                    for p_map in service_instance.service.port_mapping
                ]
            ),
        )
        return service.model_dump(exclude_defaults=True)

    def deploy_service_instance(self, service_instance: ServiceInstance):
        service_dict = self.generate_service(service_instance)
        deployment_dict = self.generate_deployment(service_instance)
        with open(
            f"{ROHE_PATH}/temp/k8s_deployment/{service_instance.id}.yml", "w"
        ) as file:
            yaml.dump(deployment_dict, file)
            file.write("\n---\n")
            yaml.dump(service_dict, file)

        utils.create_from_yaml(
            self.client, f"{ROHE_PATH}/temp/deployment/{service_instance.id}.yml"
        )
