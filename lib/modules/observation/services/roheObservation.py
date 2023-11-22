import traceback
import qoa4ml.qoaUtils as qoaUtils
import sys, uuid, time, copy
import argparse
import pymongo
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
# from lib.services.observation.roheAgenStreaming import RoheObservationAgent
from lib.rohe.restService import RoheRestObject
from flask import jsonify, request
import docker
DEFAULT_DOCKER_MOUNT = {ROHE_PATH+"/core":{"bind":"/agent/core", "mode":"ro"},
                        ROHE_PATH+"/userModule":{"bind":"/agent/userModule", "mode":"ro"},
                        ROHE_PATH+"/lib":{"bind":"/agent/lib", "mode":"ro"},
                        ROHE_PATH+"/config":{"bind":"/agent/configurations", "mode":"ro"},
                        ROHE_PATH+"/temp/agent/":{"bind":"/agent/data/", "mode":"rw"}}


class RoheRegistration(RoheRestObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        # Init Database connection
        self.db_config = self.conf["database"]
        self.connector_config = self.conf["connector"]
        self.collector_config = self.conf["collector"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.collection = self.db[self.db_config["collection"]]
        self.set_logger_level(int(self.conf["logging_level"]))
    
    def get_app(self,appName):
        # Get application configuration from database
        # Prepare query pipeline
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "appName": {"$last": "$appName"},"userID": {"$last": "$userID"}, "runID": {"$last": "$runID"}, "timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
        app_list = list(self.collection.aggregate(pipeline))
        # Get application from application list
        for app in app_list:
            if app["appName"] == appName:
                return app
        return None
    
    def update_app(self,metadata):
        # update application configuration
        return self.collection.insert_one(metadata)


    def generate_agent_conf(self, metadata):
        # Database configuration
        agent_db_config = copy.deepcopy(self.db_config)
        agent_db_config["db_name"] = "application_"+metadata["appName"]+"_"+metadata["appID"]
        agent_db_config["metric_collection"] = "metric_collection_"+metadata["runID"]
        # Collector configuration
        collector_config = copy.deepcopy(self.collector_config)
        for key in list(collector_config.keys()):
            collector_i = collector_config[key]
            i_config = collector_i["conf"]
            i_config["exchange_name"] = str(metadata["appName"])+"_exchange"
            i_config["in_routing_key"] = str(metadata["appName"])+".#"

        agent_config ={}
        agent_config["database"] = agent_db_config
        agent_config["collector"] = collector_config
        return agent_config

    def register_app(self,appName, runID, userID):
        # Create new application configuration and push to database
        metadata = {}
        metadata["appName"] = appName
        metadata["runID"] = runID
        metadata["userID"] = userID
        metadata["appID"] = str(uuid.uuid4())
        metadata["db"] = "application_"+appName+"_"+metadata["appID"]
        metadata["timestamp"] = time.time()
        metadata["client_count"] = 1
        metadata["agent_config"] = self.generate_agent_conf(metadata)
        self.collection.insert_one(metadata)
        return metadata

    def post(self):
        # Functon to handle POST request
        if request.is_json:
            args = request.get_json(force=True)
            response = {}
            if "appName" in args:
                appName = args["appName"]
                runID = args["runID"]
                userID = args["userID"]
                app = self.get_app(appName)
                if app == None:
                    metadata = self.register_app(appName, runID, userID)
                    response[appName] = "Application {} created for user {} with run ID: {}".format(appName, userID, runID)
                else:
                    response[appName] = "Application already exist"
                    metadata = app
                    metadata["client_count"] += 1
                    metadata["timestamp"] = time.time()
                    metadata["appID"] = copy.deepcopy(metadata["_id"])
                    metadata.pop("_id")
                    self.update_app(metadata)
                

                # TO DO
                # Check userID, role, stage_id, instanceID

                # Prepare connector for QoA Client
                
                connector = copy.deepcopy(self.connector_config)
                for key in list(connector.keys()):
                    connector_i = connector[key]
                    i_config = connector_i["conf"]
                    i_config["exchange_name"] = str(appName)+"_exchange"
                    i_config["out_routing_key"] = str(appName)
                    if "userID" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["userID"]
                    if "stageID" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["stageID"]
                    if "instanceID" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["instanceID"]
                    i_config["out_routing_key"] = i_config["out_routing_key"]+".client"+str(metadata["client_count"])
                response["appID"] = metadata["appID"]
                response["connector"] = connector
                

            else:
                response["Error"] = "Application name not found"
            
        return jsonify({'status': "success", "response":response})

class RoheObservation(RoheRestObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        # Init database connection
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.collection = self.db[self.db_config["collection"]]
        self.set_logger_level(int(self.conf["logging_level"]))
        self.docker_client = docker.from_env()
        # self.docker_client = docker.DockerClient(base_url= "tcp://130.233.101.62:2375")
        if "agent_dict" not in globals():
            global agent_dict 
            agent_dict = {}

    def start_docker(self, image, appName):
        container = self.docker_client.containers.run(image,volumes=DEFAULT_DOCKER_MOUNT, remove=True, detach=True, environment={'APP_NAME':appName,'ROHE_PATH':"/agent/"})
        return container

    def update_app(self,metadata):
        # update application configuration
        return self.collection.insert_one(metadata)
    
    def get_app(self,appName):
        # Create sorted pipepline to query application list
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "appName": {"$last": "$appName"},"userID": {"$last": "$userID"}, "runID": {"$last": "$runID"}, "timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
        app_list = list(self.collection.aggregate(pipeline))
        for app in app_list:
            # return app with its configuration
            if app["appName"] == appName:
                return app
        return None
    
    def show_agent(self):
        # Show list of agent and its status for debugging
        self.log("Agent: {}".format(agent_dict), 1)
        for agent in agent_dict:
            self.log("{}".format(agent), 1)

    
    def post(self):
        # Processing POST request
        response = {}
        if request.is_json:
            # parse json request
            args = request.get_json(force=True)
            self.show_agent() # for debugging
            if "appName" in args:
                # Check application info from the request
                appName = args["appName"]
                # Get application configuration from database
                app = self.get_app(appName)
                print(app)
                if app == None:
                    # Application has not been registered 
                    response[appName] = "Application {} not exist".format(appName)
                else:
                    # If application exist
                    if "command" in args:
                        # Check command
                        command = args["command"]
                        metadata = app
                        if command == "start":
                            # Check agent of the application status
                            if metadata["_id"] in agent_dict:
                                # If agent is created locally
                                agent = agent_dict[metadata["_id"]]
                                if agent["status"] != 1:
                                    agent["docker"] = self.start_docker(str(self.conf["agent_image"]), appName)
                                    agent["status"] = 1
                            else:
                                # If agent is not found - create new agent and start
                                docker_agent = self.start_docker(str(self.conf["agent_image"]), appName)
                                agent = {"docker": docker_agent, "status": 1}
                                agent_dict[metadata["_id"]] = agent
                            if "stream_config" in args:
                                metadata["appID"] = copy.deepcopy(metadata["_id"])
                                metadata.pop("_id")
                                metadata["agent_config"]["stream_config"] = args["stream_config"]
                                self.update_app(metadata)
                            self.show_agent() # for debugging
                            # create a response
                            response[appName] = "Application agent for application '{}' started ".format(appName)
                        if command == "log":
                            if metadata["_id"] in agent_dict:
                                agent = agent_dict[metadata["_id"]]
                                docker_agent = agent["docker"]
                                
                                print(docker_agent.logs(tail=20))


                        if command == "stop":
                            if metadata["_id"] in agent_dict:
                                # if agent exist locally
                                agent = agent_dict[metadata["_id"]]
                                if agent["status"] == 1:
                                    # if ageent is running
                                    docker_agent = agent["docker"]
                                    docker_agent.stop()
                                    agent["status"] = 0
                                    
                            # create a response
                            response[appName] = "Application agent for {} stopped ".format(appName)
                        if command == "delete":
                            if metadata["_id"] in agent_dict:
                                # if agent exist locally
                                agent_dict.pop(metadata["_id"])
                                # To do: 
                                # kill the agent
                            # Delete the application from databased
                            self.collection.delete_many({"appName":appName})
                            # create a response
                            response[appName] = "Application agent for {} deleted ".format(appName)
                        if command == "kill_all_agent":
                            for agent in list(agent_dict.keys()):
                                agent_dict[agent]["status"] = 0
                                agent_dict[agent]["docker"].stop()
        # Return the response
        return jsonify({'status': "success", "response":response})
