import json
import time

import networkx as nx
import yaml

from . import k3s


def show_pod(core_client):
    ret = core_client.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        print(f"{i.status.pod_ip,}\t{i.metadata.namespace}\t{i.metadata.name}")


def profiling_deploy(
    host, port, deploy_namespace, testingtime, scales, uconf, key=None
):
    # Parse the input args

    # with open(args.key, 'r') as key_file:
    #     key = key_file.read().rstrip()

    print("Running Profiling")
    user_config = json.load(open(uconf))
    conv_conf = k3s.convert_boolean(user_config)
    user_graph = nx.cytoscape_graph(conv_conf)

    kube_client_apps, kube_client_core = k3s.get_kube_client(host, port, key=None)
    show_pod(kube_client_core)

    for scale in scales.values():
        node_count = 0
        deploy_ls = []
        service_ls = []
        for name_node in list(user_graph.nodes):
            node = user_graph.nodes[name_node]
            node_deploy, service_deploy = yaml.full_load_all(
                open(node["path"] + node["value"] + "-deployment.yaml")
            )
            node_deploy["spec"]["replicas"] = int(scale[node["value"]])
            deploy_reps = kube_client_apps.create_namespaced_deployment(
                namespace=deploy_namespace, body=node_deploy
            )
            service_reps = kube_client_core.create_namespaced_service(
                namespace=deploy_namespace, body=service_deploy
            )

            deploy_ls.append(deploy_reps.metadata.name)
            service_ls.append(service_reps.metadata.name)
            node_count += 1

        print("Start testing with scale: " + str(scale))
        time.sleep(20)
        show_pod(kube_client_core)

        time.sleep(testingtime * 60)
        for i in range(node_count):
            kube_client_apps.delete_namespaced_deployment(
                name=deploy_ls[i], namespace=deploy_namespace
            )
            kube_client_core.delete_namespaced_service(
                name=service_ls[i], namespace=deploy_namespace
            )
        print("Stop testing with scale: " + str(scale))
        # time.sleep(20)
        # show_pod(kube_client_core)
        time.sleep(60)
