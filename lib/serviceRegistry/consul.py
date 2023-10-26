import requests, json
import logging, uuid

headers = {
    'Content-Type': 'application/json'
}

class consulClient(object):
    def __init__(self, config) -> None:
        """
        Example config:
        config = {
            "url": "http://127.0.0.1:8500",
            "token": None,
            "datacenter": None,
            "adapter": None
        }
        """
        if "url" in config:
            self.url = config["url"]
        else:
            self.url = "http://localhost:8500",
            logging.debug("Consul ULR is not set! Using defaul localhost")
        self.registerLink = self.url+"/v1/agent/service/register"
        self.deregisterLink = self.url+"/v1/agent/service/deregister/"
        self.getServiceLink = self.url+"/v1/catalog/services"

    def serviceRegister(self, name:str, id:str="", tag:list=None, address:str="", metadata:dict=None, port:int=0, kind:str="", Check=None, Checks=None, enableTagOverride:bool=False, Weight=None):
        service_conf = {"Name": name}

        if id == "":
            id = str(uuid.uuid4())
        if address != "":
            service_conf["Address"] = address
        if metadata != None:
            service_conf["Meta"] = metadata
        if kind != "":
            service_conf["Kind"] = kind
        if tag != None:
            service_conf["Tags"] = tag
        
        service_conf["ID"] = id
        service_conf["Port"] = port
        service_conf["EnableTagOverride"] = enableTagOverride

        response = requests.put(url=self.registerLink, headers=headers, data=json.dumps(service_conf))
        
        if response.status_code == 200:
            return id
        else:
            logging.error("Unable to register for service {}".format(name))
            return None
    
    def serviceDeregister(self, id):
        response = requests.put(url=self.deregisterLink+str(id))
        if response.status_code == 200:
            return True
        else:
            logging.error("Unable to register for service {}".format(id))
            return False
        
    
    def getServices(self, dc="", node_meta="", ns ="", service_name=""):
        query_conf ={}
        if service_name != "":
            query_conf["filter"] = "ServiceName=={}".format(service_name)
        response = requests.get(url=self.getServiceLink, params=query_conf)
        print(response.content)

"""
# Example code
# Document: https://developer.hashicorp.com/consul/api-docs/catalog#list-services

import os, sys
ROHE_PATH = os.getenv('ROHE_PATH')
sys.path.append(ROHE_PATH)

consul_conf = {
    "url": "http://195.148.22.62:8500"
}

from lib.serviceRegistry.consul import consulClient

client = consulClient(consul_conf)

service_id = client.serviceRegister("mongo", tag=["test", "demo1"])
if service_id != None:
    print(service_id, ": Registered")

response = client.serviceDeregister(service_id)
if response:
    print(service_id, ": Deregistered")

"""