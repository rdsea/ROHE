import argparse
import time

from qoa4ml.qoa_client import QoaClient
from qoa4ml.utils import qoa_utils

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument(
        "--connector", help="Connector config file", default="../conf/connector.json"
    )
    parser.add_argument(
        "--metric", help="Connector config file", default="../conf/metrics.json"
    )
    parser.add_argument(
        "--client", help="Client config file", default="../conf/node_conf.json"
    )

    args = parser.parse_args()

    node_conf = qoa_utils.load_config(args.client)
    connector_conf = qoa_utils.load_config(args.connector)
    metric_conf = qoa_utils.load_config(args.metric)
    docker_metric = metric_conf["docker"]
    physical_metric = metric_conf["physical"]
    interval = node_conf["monitor_interval"]

    qoa_client = QoaClient(
        client_conf=node_conf, connector_conf=connector_conf, metric_conf=docker_metric
    )

    qoa_utils.sys_monitor_flag = True
    qoa_utils.doc_monitor_flag = True
    qoa_utils.sys_monitor(qoa_client, interval, physical_metric)
    qoa_utils.docker_monitor(qoa_client, interval, detail=True)
    # docker_metric = qoa_client.get_metric(list(docker_metric.keys()))
    # client = docker.from_env()
    while True:
        # # client = docker.DockerClient(base_url='unix:///var/run/docker.sock')

        # # print(type(client.containers))
        # sum_cpu = 0
        # sum_memory = 0
        # for containers in client.containers.list():
        #     # print(containers.name)
        #     stats = containers.stats(decode=None, stream = False)
        #     # print(stats)
        #     UsageDelta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']

        #     SystemDelta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']

        #     len_cpu = stats['cpu_stats']['online_cpus']

        #     percentage = (UsageDelta / SystemDelta) * len_cpu * 100

        #     percent = round(percentage, 2)
        #     sum_cpu += percent
        #     sum_memory += stats["memory_stats"]["usage"]

        #     # print(stats['name'],":\n CPU:", percent,"%")
        # docker_metric["docker_cpu"].set(sum_cpu)
        # docker_metric["docker_memory"].set(sum_memory)
        # qoa_client.report()
        time.sleep(5)
        print("Sending")
