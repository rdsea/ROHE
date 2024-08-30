import copy
import json

import networkx as nx
import yaml


def convert_boolean(dict_obj):
    # Convert string boolean to True/False value
    for key in dict_obj:
        try:
            if isinstance(dict_obj[key], str):
                if isinstance(eval(dict_obj[key]), bool):
                    dict_obj[key] = eval(dict_obj[key])
        except Exception as e:
            print("Unable to convert some attribute:", e)


def get_edges(graph, config):
    # Return list of edge inform of dictionary
    edge_list = list(graph.edges)
    edges_dict = {}
    for edge in edge_list:
        if edge[0] not in edges_dict:
            edges_dict[edge[0]] = []
        temp_link = copy.deepcopy(config)
        url = copy.deepcopy(temp_link["configuration"]["url"])
        temp_link["configuration"]["url"] = url.replace("0.0.0.0", edge[1] + "-service")
        edges_dict[edge[0]].append(temp_link)
    return edges_dict


def generate_node_configuration(node, edge, config):
    # Build the task configuration for each node base on default configuration
    task_config = config.copy()
    task_config["task_configuration"] = node["task_configuration"]
    if str(node["upstream"]) == "None":
        task_config["upstream"] = config["inter_communication"]
    else:
        task_config["upstream"] = node["upstream"]
    if str(node["downstream"]) == "None":
        task_config["downstream"] = edge
    else:
        task_config["downstream"] = node["downstream"]
    task_config.pop("inter_communication", None)
    with open(node["path"] + "config.json", "w") as fp:
        json.dump(task_config, fp, indent=4)


def generate_graph_configuration(user_config, default_config):
    convert_boolean(user_config)
    user_pipeline = nx.cytoscape_graph(user_config)
    edges = get_edges(user_pipeline, default_config["inter_communication"][0])
    for node in list(user_pipeline.nodes):
        edge = edges[node] if (node in edges) else None
        generate_node_configuration(user_pipeline.nodes[node], edge, default_config)
    return user_pipeline


def generate_pod_deployment(node, def_pod_deploy):
    pod_deploy = copy.deepcopy(def_pod_deploy)
    pod_deploy["metadata"]["name"] = node["value"] + "-deployment"
    pod_deploy["metadata"]["labels"]["app"] = node["value"]
    pod_deploy["spec"]["selector"]["matchLabels"]["app"] = node["value"]
    pod_deploy["spec"]["template"]["metadata"]["labels"]["app"] = node["value"]
    pod_deploy["spec"]["template"]["spec"]["containers"][0]["name"] = node["value"]
    pod_deploy["spec"]["template"]["spec"]["containers"][0]["image"] = node["image"]
    return pod_deploy
    # print((pod_deploy["spec"]["template"]["spec"]["containers"]))


def generate_service_deployment(node, def_service_deploy):
    service_deploy = copy.deepcopy(def_service_deploy)
    service_deploy["metadata"]["name"] = node["value"] + "-service"
    service_deploy["spec"]["selector"]["app"] = node["value"]
    return service_deploy
    # print((pod_deploy["spec"]["template"]["spec"]["containers"]))


def generate_graph_deployment(user_pipeline, def_pod_deploy, def_service_deploy):
    for name_node in list(user_pipeline.nodes):
        node = user_pipeline.nodes[name_node]
        pod_deploy = generate_pod_deployment(node, def_pod_deploy)
        service_deploy = generate_service_deployment(node, def_service_deploy)
        with open(node["path"] + node["value"] + "-deployment.yaml", "w") as fp:
            yaml.dump_all(
                [pod_deploy, service_deploy], fp, indent=2, explicit_start=True
            )


def generate_deployment_k3s(
    user_config_path, default_com_config_path, default_deployment_path
):
    user_config = json.load(open(user_config_path))
    default_config = json.load(open(default_com_config_path))
    def_pod_deploy, def_service_deploy = yaml.full_load_all(
        open(default_deployment_path)
    )
    user_pipeline = generate_graph_configuration(user_config, default_config)

    generate_graph_deployment(user_pipeline, def_pod_deploy, def_service_deploy)

    # nx.draw(user_pipeline, with_labels=True, font_weight='bold')
    # plt.show()
