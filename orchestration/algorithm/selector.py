from ..resource.Node import Node
from operator import itemgetter


def filtering_node(list_node, criteria_dict):
    avail_node_list = []
    for node in list_node:
        avail = True
        for key in criteria_dict:
            if (node.get_resource_av[key] <= criteria_dict[key]):
                avail = False
                break
        if avail == True:
            avail_node_list.append(node)
    return avail_node_list
    
def sort_by(list_node, main_criterion):
    return sorted(list_node, key=itemgetter(main_criterion))

def selecting_node(list_node, main_criterion, strategy):
    if strategy != 0: # Not first fit
        sort_by(list_node, main_criterion)
        if strategy == 1: # Best fit
            return list_node[-1]
        elif strategy == 2: # Worst fit
            return list_node[0]
    else: # First fit
        return list_node[0]