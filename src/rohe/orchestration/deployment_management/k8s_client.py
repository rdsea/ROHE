from pathlib import Path

import yaml
from kubernetes import client, config, utils

from ...variable import ROHE_PATH
from ..resource_management import ServiceInstance


class K8sClient:
    def __init__(self):
        config.load_kube_config()
        self.api_client = client.ApiClient()

        Path(f"{ROHE_PATH}/temp/k8s_deployment").mkdir(parents=True, exist_ok=True)

    def generate_deployment(self, service_instance: ServiceInstance):
        task_name = service_instance.service.name
        node_name = service_instance.node.name
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=f"{task_name}-{node_name}",
                labels={"app": task_name},
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": task_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": task_name}),
                    spec=client.V1PodSpec(
                        restart_policy="Always",
                        node_selector={"kubernetes.io/hostname": node_name},
                        containers=[
                            client.V1Container(
                                name=task_name,
                                image=service_instance.service.image,
                                image_pull_policy="Always",
                                ports=[
                                    client.V1ContainerPort(container_port=port)
                                    for port in service_instance.service.ports
                                ],
                                env=[
                                    client.V1EnvVar(
                                        name="NODE_NAME",
                                        value_from=client.V1EnvVarSource(
                                            field_ref=client.V1ObjectFieldSelector(
                                                field_path="spec.nodeName"
                                            )
                                        ),
                                    ),
                                    client.V1EnvVar(
                                        name="POD_ID",
                                        value_from=client.V1EnvVarSource(
                                            field_ref=client.V1ObjectFieldSelector(
                                                field_path="metadata.name"
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
        return self.api_client.sanitize_for_serialization(deployment)

    def generate_service(self, service_instance: ServiceInstance):
        task_name = service_instance.service.name
        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=f"{task_name}-service",
            ),
            spec=client.V1ServiceSpec(
                ports=[
                    client.V1ServicePort(
                        port=p_map.con_port, target_port=p_map.phy_port
                    )
                    for p_map in service_instance.service.port_mapping
                ]
            ),
        )
        return self.api_client.sanitize_for_serialization(service)

    def deploy_service_instance(self, service_instance: ServiceInstance):
        service_dict = self.generate_service(service_instance)
        deployment_dict = self.generate_deployment(service_instance)
        output_path = f"{ROHE_PATH}/temp/k8s_deployment/{service_instance.id}.yml"
        with open(output_path, "w") as file:
            yaml.dump(deployment_dict, file)
            file.write("\n---\n")
            yaml.dump(service_dict, file)

        utils.create_from_yaml(self.api_client, output_path)
