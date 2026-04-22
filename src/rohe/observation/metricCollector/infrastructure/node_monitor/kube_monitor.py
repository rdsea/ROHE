"""Probe the well-known service-account issuer endpoint on a Kubernetes API server.

Credentials are read from the environment:
    K8S_BEARER_TOKEN  required  serviceaccount JWT
    K8S_API_HOST      required  e.g. https://edge-k3s-r1.example.internal:6443
"""

import os

import kubernetes.client
from kubernetes.client.rest import ApiException


def main() -> None:
    token = os.environ.get("K8S_BEARER_TOKEN")
    host = os.environ.get("K8S_API_HOST")
    if not token or not host:
        raise RuntimeError(
            "K8S_BEARER_TOKEN and K8S_API_HOST must be set in the environment"
        )

    configuration = kubernetes.client.Configuration()
    configuration.api_key["authorization"] = token
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = host
    configuration.verify_ssl = True

    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.WellKnownApi(api_client)
        try:
            api_response = (
                api_instance.get_service_account_issuer_open_id_configuration()
            )
            print(api_response)
        except ApiException as e:
            print(
                f"Exception when calling WellKnownApi->get_service_account_issuer_open_id_configuration: {e}\n"
            )


if __name__ == "__main__":
    main()
