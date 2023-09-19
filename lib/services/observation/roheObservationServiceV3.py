import traceback
import qoa4ml.qoaUtils as qoaUtils
import sys, uuid, time, copy
import argparse
import pymongo
main_path = config_file = qoaUtils.get_parent_dir(__file__,3)
sys.path.append(main_path)
from lib.modules.observation.metricCollector.roheAgenStreaming import RoheObservationAgent
from lib.services.restService import RoheRestObject, RoheRestService
from flask import jsonify, request

DEFAULT_CONFIG_PATH="/configurations/observation/observationConfig.json"

local_agent_list = {}


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
    
    def get_app(self,app_name):
        # Get application configuration from database
        # Prepare query pipeline
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "app_name": {"$last": "$app_name"},"timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
        app_list = list(self.collection.aggregate(pipeline))
        # Get application from application list
        for app in app_list:
            if app["app_name"] == app_name:
                return app
        return None
    
    def update_app(self,metadata):
        # update application configuration
        return self.collection.insert_one(metadata)


    def generate_agent_conf(self, metadata):
        # Database configuration
        agent_db_config = copy.deepcopy(self.db_config)
        agent_db_config["db_name"] = "application_"+metadata["app_name"]+"_"+metadata["appID"]
        agent_db_config["metric_collection"] = "metric_collection"
        # Collector configuration
        collector_config = copy.deepcopy(self.collector_config)
        for key in list(collector_config.keys()):
            collector_i = collector_config[key]
            i_config = collector_i["conf"]
            i_config["exchange_name"] = str(metadata["app_name"])+"_exchange"
            i_config["in_routing_key"] = str(metadata["app_name"])+".#"

        agent_config ={}
        agent_config["database"] = agent_db_config
        agent_config["collector"] = collector_config
        return agent_config

    def register_app(self,app_name):
        # Create new application configuration and push to database
        metadata = {}
        metadata["app_name"] = app_name
        metadata["appID"] = str(uuid.uuid4())
        metadata["db"] = "application_"+app_name+"_"+metadata["appID"]
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
            if "application" in args:
                application_name = args["application"]
                app = self.get_app(application_name)
                if app == None:
                    metadata = self.register_app(application_name)
                    response[application_name] = "Application {} created".format(application_name)
                else:
                    response[application_name] = "Application already exist"
                    metadata = app
                    metadata["client_count"] += 1
                    metadata["timestamp"] = time.time()
                    metadata["appID"] = copy.deepcopy(metadata["_id"])
                    metadata.pop("_id")
                    self.update_app(metadata)
                

                # TO DO
                # Check client_id, role, stage_id, instance_name

                # Prepare connector for QoA Client

                
                connector = copy.deepcopy(self.connector_config)
                for key in list(connector.keys()):
                    connector_i = connector[key]
                    i_config = connector_i["conf"]
                    i_config["exchange_name"] = str(application_name)+"_exchange"
                    i_config["out_routing_key"] = str(application_name)
                    if "client_id" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["client_id"]
                    if "stage_id" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["stage_id"]
                    if "instance_name" in args:
                        i_config["out_routing_key"] = i_config["out_routing_key"]+"."+args["instance_name"]
                    i_config["out_routing_key"] = i_config["out_routing_key"]+".client"+str(metadata["client_count"])
                response["application_id"] = metadata["appID"]
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
    
    def get_app(self,app_name):
        # Create sorted pipepline to query application list
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "app_name": {"$last": "$app_name"},"timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
        app_list = list(self.collection.aggregate(pipeline))
        for app in app_list:
            # return app with its configuration
            if app["app_name"] == app_name:
                return app
        return None
    
    def show_agent(self):
        # Show list of agent and its status for debugging
        self.log("Agent: {}".format(local_agent_list), 1)
        for agent in local_agent_list:
            self.log("{} - {} - {}".format(agent, local_agent_list[agent].status, local_agent_list[agent].insert_db), 1)

    
    def post(self):
        # Processing POST request
        response = {}
        if request.is_json:
            # parse json request
            args = request.get_json(force=True)
            self.show_agent() # for debugging
            if "application" in args:
                # Check application info from the request
                application_name = args["application"]
                # Get application configuration from database
                app = self.get_app(application_name)
                if app == None:
                    # Application has not been registered 
                    response[application_name] = "Application {} not exist".format(application_name)
                else:
                    # If application exist
                    if "command" in args:
                        # Check command
                        command = args["command"]
                        metadata = app
                        if command == "start":
                            # Check agent of the application status
                            if metadata["_id"] in local_agent_list:
                                # If agent is created locally
                                agent = local_agent_list[metadata["_id"]]
                                if agent.status == 0:
                                    # if agent is ready
                                    agent.start()
                                elif agent.status == 2:
                                    # if agent is stopped
                                    agent.restart()
                            else:
                                # If agent is not found - create new agent and start
                                agent_config = metadata["agent_config"]
                                agent = RoheObservationAgent(agent_config)
                                local_agent_list[metadata["_id"]] = agent
                                agent.start()

                            self.show_agent() # for debugging
                            # create a response
                            response[application_name] = "Application agent for {} started ".format(application_name)

                        if command == "stop":
                            if metadata["_id"] in local_agent_list:
                                # if agent exist locally
                                agent = local_agent_list[metadata["_id"]]
                                if agent.status == 1:
                                    # if ageent is running
                                    agent.stop()
                                    self.show_agent() # for debugging
                            # create a response
                            response[application_name] = "Application agent for {} stopped ".format(application_name)
                        if command == "delete":
                            if metadata["_id"] in local_agent_list:
                                # if agent exist locally
                                local_agent_list.pop(metadata["_id"])
                                # To do: 
                                # kill the agent
                            # Delete the application from databased
                            self.collection.delete_many({"app_name":application_name})
                            # create a response
                            response[application_name] = "Application agent for {} deleted ".format(application_name)
        # Return the response
        return jsonify({'status': "success", "response":response})


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    #parser.add_argument('--path', help='default config path', default="/configurations/observation/observationConfig.json")
    parser.add_argument('--port', help='default port', default=5010)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    #config_path = args.path
    port = int(args.port)

    # load configuration file
    if not config_file:
        config_file = main_path+DEFAULT_CONFIG_PATH
        print(config_file)
    try:
        configuration = qoaUtils.load_config(config_file)
        observationService = RoheRestService(configuration)
        observationService.add_resource(RoheObservation, '/agent')
        observationService.add_resource(RoheRegistration, '/registration')
        observationService.run(port=port)
    except:
        traceback.print_exc()
