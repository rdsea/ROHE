from utilities import k3s
import argparse, json, yaml, time
import networkx as nx


if __name__ == '__main__':
    # Parse the input args
    parser = argparse.ArgumentParser(description="Deploy application for profiling")
    parser.add_argument('--uconf', help='configuration file', default='./user_dag.json')
    parser.add_argument('--host', help='k3s host', default='localhost')
    parser.add_argument('--port', help='k3s port', default=6443)
    parser.add_argument('--key', help='k3s key', default='./key.txt')
    parser.add_argument('--scale', help='deployment scales', default='./scale.txt')
    parser.add_argument('--namespace', help='deployment namespace', default='default')
    parser.add_argument('--time', help='testing time', default=10)
    args = parser.parse_args()

    host = args.host
    port = args.port
    deploy_namespace = args.namespace
    testingtime = int(args.time)
    with open(args.key, 'r') as key_file:
        key = key_file.read().rstrip()
    
    with open(args.scales, 'r') as scales_file:
        scales = scales_file.readlines()

    user_config = json.load(open(args.uconf))
    conv_conf = k3s.convert_boolean(user_config)
    user_graph = nx.cytoscape_graph(conv_conf)

    kube_client_apps, kube_client_core = k3s.get_kube_client(host, port, key)

    for scale in scales:
        scale_ls = scale.split(" ")
        node_count = 0
        deploy_ls = []
        service_ls = []
        for name_node in list(user_graph.nodes):
            node = user_graph.nodes[name_node]
            node_deploy, service_deploy = yaml.full_load_all(open(node["path"]+node['value']+'-deployment.yaml'))
            node_deploy['spec']['replicas'] = int(scale_ls[node_count])
            deploy_reps = kube_client_apps.create_namespaced_deployment(namespace=deploy_namespace,body=node_deploy)
            service_reps = kube_client_core.create_namespaced_service(namespace=deploy_namespace,body=service_deploy)

            deploy_ls.append(deploy_reps.metadata.name)
            service_ls.append(service_reps.metadata.name)
            node_count += 1


        print("Start testing with scale: " + str(scale))
        time.sleep(testingtime*60)
        for i in range(node_count):
            kube_client_apps.delete_namespaced_deployment(name=deploy_ls[i],namespace=deploy_namespace)
            kube_client_core.create_namespaced_service(name=service_ls[i],namespace=deploy_namespace)
        print("Stop testing with scale: " + str(scale))
        time.sleep(60)
        

