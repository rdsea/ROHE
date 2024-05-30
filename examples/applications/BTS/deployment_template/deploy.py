# import kubernetes.client
# from kubernetes.client.rest import ApiException
# from pprint import pprint
import time

import kubernetes.client
import yaml
from kubernetes import config, dynamic
from kubernetes.client import api_client

# import datetime
# import pytz
# from os import path


def run():
    # Define the bearer token we are going to use to authenticate.
    # See here to create the token:
    # https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/
    aConfiguration = config.load_kube_config()
    # client = dynamic.DynamicClient(
    #     api_client.ApiClient(configuration=aConfiguration)
    # )
    service_config = yaml.safe_load(open("./data_preprocessing_service.yaml"))
    # fetching the service api
    # api = client.resources.get(api_version="v1", kind="Service")
    # service = api.create(body=service_config, namespace="default")
    # print(service)
    client = dynamic.DynamicClient(
        api_client.ApiClient(configuration=config.load_kube_config())
    )

    # fetching the service api
    api = client.resources.get(api_version="v1", kind="Service")

    # Creating service `frontend-service` in the `default` namespace

    service = api.create(body=service_config, namespace="default")

    print("\n[INFO] service `frontend-service` created\n")

    # Listing service `frontend-service` in the `default` namespace
    service_created = api.get(name=service.metadata.name, namespace="default")

    print("%s\t%s" % ("NAMESPACE", "NAME"))
    print(
        "%s\t\t%s\n"
        % (service_created.metadata.namespace, service_created.metadata.name)
    )

    # Patching the `spec` section of the `frontend-service`

    service_config["spec"]["ports"] = [
        {"name": "new", "port": 8080, "protocol": "TCP", "targetPort": 8080}
    ]

    service_patched = api.patch(
        body=service_config, name=service.metadata.name, namespace="default"
    )

    print("\n[INFO] service `frontend-service` patched\n")
    print("%s\t%s\t\t\t%s" % ("NAMESPACE", "NAME", "PORTS"))
    print(
        "%s\t\t%s\t%s\n"
        % (
            service_patched.metadata.namespace,
            service_patched.metadata.name,
            service_patched.spec.ports,
        )
    )

    # Deleting service `frontend-service` from the `default` namespace
    service_deleted = api.delete(
        name=service.metadata.name, body={}, namespace="default"
    )

    print("\n[INFO] service `frontend-service` deleted\n")

    # Create a ApiClient with our config
    # with kubernetes.client.ApiClient(aConfiguration) as api_client:
    # Create an instance of the API class
    # api_instance = kubernetes.client.AppsV1Api(api_client)
    # with open("./data_preprocessing_deployment.yaml") as f:
    #     service = yaml.safe_load(f)
    # try:
    #     api_response = api_instance.create_namespaced_deployment(body=body, namespace="default")
    #     print("Deployment created: \n %s" % type(api_response))
    #     body = api_response
    # except ApiException as e:
    #     print("Exception when calling AdmissionregistrationApi->get_api_group: %s\n" % e)

    # time.sleep(20)
    # body = api_instance.read_namespaced_deployment(name="data-proprocessing-deployment", namespace="default")
    # body.spec.template.metadata.annotations = {
    #     "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow()
    #     .replace(tzinfo=pytz.UTC)
    #     .isoformat()
    # }
    # name = body.metadata.name
    # try:
    #     api_response = api_instance.patch_namespaced_deployment(name=name, namespace="default", body=body)
    #     print("Deployment updated: \n%s" % type(api_response))
    # except ApiException as e:
    #     print("Exception when calling AppsV1Api->patch_namespaced_deployment: %s\n" % e)

    # time.sleep(120)
    # try:
    #     api_response = api_instance.delete_namespaced_deployment(name="data-proprocessing-deployment", namespace="default")
    #     print("Deployment created: \n %s" % api_response.status)
    # except ApiException as e:
    #     print("Exception when calling AdmissionregistrationApi->get_api_group: %s\n" % e)


if __name__ == "__main__":
    run()
