import sys
import qoa4ml.utils as utils
import numpy as np
import traceback
import yaml, os
from jinja2 import Environment, FileSystemLoader



temporary_folder = utils.get_parent_dir(__file__,1)+"/temp"
template_folder = utils.get_parent_dir(__file__,2)+"/templates"
jinja_env = Environment(loader=FileSystemLoader(template_folder))



def filtering_node(nodes, service):
    key_list = []
    for key in nodes:
        node_flag = False
        av_cpu = nodes[key].cpu["capacity"] - nodes[key].cpu["used"]
        av_mem = nodes[key].memory["capacity"]["rss"] - nodes[key].memory["used"]["rss"]
        if service.cpu <= av_cpu and service.memory["rss"] <= av_mem:
            for dev in service.accelerator:
                if service.accelerator[dev] == 0:
                    node_flag = True
                else:
                    for device in nodes[key].accelerator:
                        av_accelerator = nodes[key].accelerator[device]["capacity"] - nodes[key].accelerator[device]["used"]
                        if nodes[key].accelerator[device]["type"] == dev and service.accelerator[dev] < av_accelerator:
                            node_flag = True
        if node_flag:
            key_list.append(key)

    return key_list
    
def ranking(nodes, keys, service, weights={"cpu":1,"memory":1}):
    node_ranks = {}
    for key in keys:
        selected_node = nodes[key]

        remain_proc = np.sort((np.array(selected_node.processor["capacity"]) - np.array(selected_node.processor["used"])))
        req_proc = np.array(service.processor)
        req_proc.resize(remain_proc.shape)
        req_proc = np.sort(req_proc)
        remain_proc = remain_proc-req_proc
        if np.any(remain_proc < 0):                                      
            node_ranks[key] = -1
        else:
            rank_proc = np.sum(remain_proc)/(remain_proc.size*100)

            remain_mem = selected_node.memory["capacity"]["rss"]-selected_node.memory["used"]["rss"]
            rank_mem = (remain_mem - service.memory["rss"])/selected_node.memory["capacity"]["rss"]
            node_ranks[key] = weights["cpu"]*rank_proc+weights["memory"]*rank_mem

    node_ranks = {k: v for k, v in node_ranks.items() if v > 0}
    return node_ranks

def selecting_node(node_ranks, strategy=0):
    node_id = -1
    try:
        if strategy == 0: # first fit
            node_id = list(node_ranks.keys())[0]
        else:
            sort_nodes = {k: v for k, v in sorted(node_ranks.items(), key=lambda item: item[1])}
            if strategy == 1: # best fit
                node_id = list(sort_nodes.keys())[-1]
            elif strategy == 2: # worst fit
                node_id = list(sort_nodes.keys())[0]
    except Exception as e:
        print("[ERROR] - Error {} while sellecting node: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())

    return node_id


def assign(nodes, node_id, service):
    if node_id in nodes:
        nodes[node_id].allocate(service)
        # print("assign success")

def allocate_service(service, nodes, weights, strategy, replicas):
    for i in range(replicas):
        fil_nodes = filtering_node(nodes, service)
        ranking_list = ranking(nodes, fil_nodes,service,weights)
        # print(ranking_list)
        node_id = selecting_node(ranking_list,strategy)
        if node_id == -1:
            print("Cannot find node for service: {}".format(service))
        else:
            assign(nodes, node_id, service)

def deallocate_service(service, nodes, weights, strategy):
    pass


def generate_deployment(nodes, service):
    jinja_var = {}
    deployment = jinja_env.get_template("deployment_templates.yaml")
    folder_path = temporary_folder+"/"+service.name
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    for node in service.node_list:
        jinja_var["node_name"] = nodes[node].name
        jinja_var["task_name"] = service.name
        jinja_var["image_name"] = service.image
        jinja_var["service_replica"] = service.replicas
        jinja_var["ports"] = service.ports
        jinja_var["port_mapping"] = service.port_mapping
        file_path = folder_path+"/"+nodes[node].name+".yaml"
        with open(file_path, "w") as f:
            f.write(deployment.render(jinja_var))

def ex_orchestrate(nodes, services, service_queue):
    while not service_queue.empty():
        p_service = service_queue.get()
        replica = p_service.replicas
        l_nodes = {}
        if p_service.id in services:
            if p_service.replicas == services[p_service.id].replicas:
                continue
            elif p_service.replicas < services[p_service.id].replicas:
                deallocate_service(p_service, nodes, service_queue.config["weights"], service_queue.config["strategy"])
                continue
            else:
                replica = p_service.replicas - services[p_service.id].replicas
                l_nodes = services[p_service.id].node_list
        allocate_service(p_service, nodes, service_queue.config["weights"], service_queue.config["strategy"], replica)
        generate_deployment(nodes, p_service)
        for node in l_nodes:
            if node in p_service.node_list:
                p_service.node_list[node] += l_nodes[node]
            else:
                p_service.node_list[node] = l_nodes[node]
        p_service.status = "running"
        services[p_service.id] = p_service
        # print(p_service.config)
