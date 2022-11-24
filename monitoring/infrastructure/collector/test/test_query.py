import requests
import json
import time
PROMETHEUS = 'http://localhost:9090/'

name = "cpu"
cpu_usage_name = "node_cpu_seconds_total"
name_node = "worker_jet02"
offset = "1m"

while True:
    cpu_usage_query = '100 - (avg(rate(%s{job="%s",mode="idle"}[%s])) * 100)' % (cpu_usage_name, name_node, offset)
    response =requests.get(PROMETHEUS + '/api/v1/query', params={'query': cpu_usage_query})
    print (response.text)
    j_response = json.loads(response.text)
    data_json = j_response["data"]["result"]
    print(data_json[0]["value"][1])
    json_formatted_str = json.dumps(data_json, indent=2)
    print(json_formatted_str)
    cpu_usage_query = 'avg(%s{job="worker_jet02_gpu",statistic="val"})' %(name)
    response =requests.get(PROMETHEUS + '/api/v1/query', params={'query': cpu_usage_query})
    print (response.text)
    j_response = json.loads(response.text)
    data_json = j_response["data"]["result"]
    print(len(data_json))
    json_formatted_str = json.dumps(data_json, indent=2)
    print(json_formatted_str)
    time.sleep(1)
