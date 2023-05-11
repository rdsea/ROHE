import sys
sys.path.insert(0, '..')
from resource.resource import Node, Node_Collection, Service_Queue, Service
from operator import itemgetter
import qoa4ml.utils as utils
import argparse
import numpy as np
import traceback




def filtering_node(nodes, service):
    key_list = []
    for key in nodes.collection:
        node_flag = False
        av_cpu = nodes.collection[key].cpu["capacity"] - nodes.collection[key].cpu["used"]
        av_mem = nodes.collection[key].memory["capacity"]["rss"] - nodes.collection[key].memory["used"]["rss"]
        if service.cpu <= av_cpu and service.memory["rss"] <= av_mem:
            for dev in service.accelerator:
                if service.accelerator[dev] == 0:
                    node_flag = True
                else:
                    for device in nodes.collection[key].accelerator:
                        av_accelerator = nodes.collection[key].accelerator[device]["capacity"] - nodes.collection[key].accelerator[device]["used"]
                        if nodes.collection[key].accelerator[device]["type"] == dev and service.accelerator[dev] < av_accelerator:
                            node_flag = True
        if node_flag:
            key_list.append(key)

    return key_list
    
def ranking(nodes, keys, service, weights={"cpu":1,"memory":1}):
    node_ranks = {}
    for key in keys:
        selected_node = nodes.collection[key]

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
    if node_id in nodes.collection:
        nodes.collection[node_id].allocate(service)
        # print("assign success")
    

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Orchestration Algorithm")
    parser.add_argument('--aconf', help='Application configuration file', default="../config/application_config.json")
    parser.add_argument('--nconf', help='Node configuration file', default="../config/node_config.json")
    parser.add_argument('--sqconf', help='Service queue configuration file', default="../config/service_queue_config.json")
    args = parser.parse_args()
    sqconfig = utils.load_config(args.sqconf)
    service_queue = Service_Queue(sqconfig)

    nconfig = utils.load_config(args.nconf)

    nodes = Node_Collection()
    for key in nconfig:
        nodes.add(Node(nconfig[key]))


    aconfig = utils.load_config(args.aconf)
    services = {}
    for app in aconfig:
        for key in aconfig[app]:
            services[key] = Service(aconfig[app][key])
            service_queue.put(services[key])
            print(services[key])

    while not service_queue.empty():
        p_service = service_queue.get()
        for i in range(p_service.replicas):
            fil_nodes = filtering_node(nodes, p_service)
            ranking_list = ranking(nodes, fil_nodes,p_service,sqconfig["weights"])
            # print(ranking_list)
            node_id = selecting_node(ranking_list,sqconfig["strategy"])
            if node_id == -1:
                print("Cannot find node for service: {}".format(p_service))
            else:
                assign(nodes, node_id, p_service)

    for key in services:
        print(services[key],services[key].node_list)

    print(nodes)
        
    