import json
import time

import requests


class Crawler:
    def __init__(self, prom_host, metric_map):
        self.prom_host = prom_host
        self.metric_map = json.load(open(metric_map))

    def set_prom_host(self, prom_host):
        self.prom_host = prom_host

    def get_by_metric(self, name_node, metric):
        temp_query = f'{metric}{{job="{name_node}"}}'
        return self.get_by_query(temp_query)

    def get_by_query(self, query):
        try:
            response = requests.get(
                self.prom_host + "/api/v1/query", params={"query": query}
            )
            data_json = json.loads(response.text)["data"]["result"]
        except Exception as e:
            print(f"Error while querying data: {e}")
        result = {"time": time.time(), "value": -1}
        try:
            result["time"] = data_json[0]["value"][0]
            result["value"] = float(data_json[0]["value"][1])
        except Exception as e:
            print(f"Error while parsing data: {e}")
        return result


class Node:
    def __init__(self, name_node, accesspoint, prom_host, metric_map):
        self.name_node = name_node
        self.accesspoint = accesspoint
        self.prom_host = prom_host
        self.node_label = {}
        self.crawler = Crawler(prom_host, metric_map)
        self.attributes = {
            "name_node": self.name_node,
            "cpu_core": self.crawler.metric_map["cpu_core"],
            "total_mem": self.crawler.metric_map["total_mem"],
            "last_update": 0,
        }
        self.memory_cap = self.crawler.metric_map["total_mem"]
        self.cpu_core = self.crawler.metric_map["cpu_core"]
        self.node_status = 0

    def get_report(self):
        self.update()
        return self.attributes

    def set_attribute(self, attribute_dict):
        for key, value in attribute_dict:
            self.attributes[key] = value

    def set_metric_map(self, metric_dict):
        for key, _value in self.attributes:
            try:
                self.metric_map[key] = metric_dict[key]
            except Exception as e:
                print(f"Missing metric for {key}: {e}")

    def set_label(self, label):
        self.node_label[label] = True

    def remove_label(self, label):
        self.self.node_label[label] = False

    def check_label(self, label):
        if label in self.node_label:
            return self.node_label[label]
        else:
            return False

    def get_by_query(self, query, warning):
        try:
            return self.crawler.get_by_query(query)
        except Exception as e:
            self.node_status = 0
            print(warning + f"{e}")

    def get_by_name(self, metric_name, warning):
        try:
            return self.crawler.get_by_metric(self.name_node, metric_name)
        except Exception as e:
            self.node_status = 0
            print(warning + e)

    def update(self):
        self.update_cpu()
        self.update_gpu()
        self.update_mem()
        self.update_tpu()
        self.update_other_metrics()
        self.attributes["last_update"] = time.time()

    def update_cpu(self, offset="1m"):
        temp_query = '100 - (avg(rate({}{{job="{}",mode="idle"}}[{}])) * 100)'.format(
            self.crawler.metric_map["cpu_usage"]["name"],
            self.name_node,
            offset,
        )
        self.attributes["cpu_usage"] = self.get_by_query(
            temp_query, "Error while update CPU usage: "
        )["value"]

        temp_query = 'avg({}{{job="{}"}})'.format(
            self.crawler.metric_map["cpu_freq"]["name"],
            self.name_node,
        )
        self.attributes["cpu_freq"] = self.get_by_query(
            temp_query, "Error while update CPU frequency: "
        )["value"]

        self.node_status = 1

    def update_mem(self):
        self.attributes["mem_active"] = self.get_by_name(
            self.crawler.metric_map["mem_active"]["name"],
            "Error while update active memory: ",
        )["value"]
        self.attributes["mem_free"] = self.get_by_name(
            self.crawler.metric_map["mem_free"]["name"],
            "Error while update free memory: ",
        )["value"]
        self.attributes["mem_cached"] = self.get_by_name(
            self.crawler.metric_map["mem_cached"]["name"],
            "Error while update cached memory: ",
        )["value"]
        self.attributes["memory_buffered"] = self.get_by_name(
            self.crawler.metric_map["memory_buffered"]["name"],
            "Error while update buffered memory: ",
        )["value"]

        temp_query = (
            '(({}{{job="{}"}} - {}{{job="{}"}}) / {}{{job="{}"}}) * 100'.format(
                self.crawler.metric_map["mem_total"]["name"],
                self.name_node,
                self.crawler.metric_map["mem_free"]["name"],
                self.name_node,
                self.crawler.metric_map["mem_total"]["name"],
                self.name_node,
            )
        )
        self.attributes["mem_usage"] = self.get_by_query(
            temp_query, "Error while update memory usage: "
        )["value"]

    def update_gpu(self):
        # override in child classes
        pass

    def update_tpu(self):
        # override in child classes
        pass

    def update_other_metrics(self):
        # override in child classes
        pass

    def __str__(self):
        return json.dumps(self.attributes, indent=2)


class NodeJet(Node):
    def __init__(self, name_node, accesspoint, prom_host, metric_map):
        super().__init__(name_node, accesspoint, prom_host, metric_map)

    def update_cpu(self, offset="1m"):
        super().update_cpu(offset=offset)
        temp_query = '{}{{job="{}_gpu", machine_part="CPU"}}'.format(
            self.crawler.metric_map["temperature"]["name"],
            self.name_node,
        )
        self.attributes["cpu_temperature"] = self.get_by_query(
            temp_query, "Error while update CPU temperature: "
        )["value"]

    def update_gpu(self):
        temp_query = '{}{{job="{}_gpu"}}'.format(
            self.crawler.metric_map["gpu_usage"]["name"],
            self.name_node,
        )
        self.attributes["gpu_usage"] = self.get_by_query(
            temp_query, "Error while update memory usage: "
        )["value"]

        temp_query = '{}{{job="{}_gpu", machine_part="GPU"}}'.format(
            self.crawler.metric_map["temperature"]["name"],
            self.name_node,
        )
        self.attributes["gpu_temperature"] = self.get_by_query(
            temp_query, "Error while update GPU temperature: "
        )["value"]

    def update_other_metrics(self):
        temp_query = f'swap{{job="{self.name_node}_gpu", statistic="total"}}'
        self.attributes["swap_total"] = self.get_by_query(
            temp_query, "Error while update total swap memory: "
        )["value"]

        temp_query = f'swap{{job="{self.name_node}_gpu", statistic="used"}}'
        self.attributes["swap_used"] = self.get_by_query(
            temp_query, "Error while update used swap memory: "
        )["value"]


class NodeRock(Node):
    def __init__(self, name_node, accesspoint, prom_host, metric_map):
        super().__init__(name_node, accesspoint, prom_host, metric_map)

    def update_tpu(self):
        # Implement here
        pass
