
import qoa4ml.utils as utils
import sys, uuid, time, copy
import argparse
import pymongo
main_path = config_file = utils.get_parent_dir(__file__,2)
sys.path.append(main_path)



from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

# local_application_list = {}
agent_list = {}

class RoheRegistrationService(Resource):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        self.db_config = self.conf["database"]
        self.connector_config = self.conf["connector"]
        self.collector_config = self.conf["collector"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.collection = self.db[self.db_config["collection"]]
    
    def get_app(self,app_name):
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "app_name": {"$last": "$app_name"},"timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
        app_list = list(self.collection.aggregate(pipeline))
        for app in app_list:
            if app["app_name"] == app_name:
                return app
        return None
    
    def update_app(self,metadata):
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
        metadata = {}
        metadata["app_name"] = app_name
        metadata["appID"] = str(uuid.uuid4())
        metadata["db"] = "application_"+app_name+"_"+metadata["appID"]
        metadata["timestamp"] = time.time()
        metadata["client_count"] = 1
        metadata["agent_config"] = self.generate_agent_conf(metadata)
        self.collection.insert_one(metadata)
        return metadata
    
    
        
    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})

    def post(self):
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
                
                # local_application_list[application_name] = {}
                # local_application_list[application_name]["appID"] = metadata["appID"]
                # local_application_list[application_name]["client_count"] = metadata["client_count"]
                # local_application_list[application_name]["db"] = metadata["db"]


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
                
                # # Prepare QoA Agent
                # application_id = local_application_list[application_name]["appID"]
                # if application_id not in agent_list:
                #     # Database configuration
                #     agent_db_config = self.db_config.copy()
                #     agent_db_config["db_name"] = "application_"+application_name+"_"+application_id
                #     agent_db_config["metric_collection"] = "metric_collection"
                #     # Collector configuration
                #     collector_config = copy.deepcopy(self.collector_config)
                #     for key in list(collector_config.keys()):
                #         collector_i = collector_config[key]
                #         i_config = collector_i["conf"]
                #         i_config["exchange_name"] = str(application_name)+"_exchange"
                #         i_config["in_routing_key"] = str(application_name)+".#"

                #     # Agent configuration 
                #     agent_config ={}
                #     agent_config["database"] = agent_db_config
                #     agent_config["collector"] = collector_config
                #     agent = RoheObservationAgent(agent_config)
                #     agent_id = str(uuid.uuid4())
                #     agent_list[application_id] = {}
                #     agent_list[application_id][agent_id] = {}
                #     agent_list[application_id][agent_id]["agent"] = agent
                #     agent_list[application_id][agent_id]["status"] = "stop"
                #     agent_list[application_id][agent_id]["configuration"] = agent_config
                #     agent.start()

            else:
                response["Error"] = "Application name not found"
            
           
            
        return jsonify({'status': "success", "response":response})

    def put(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': True})

    def delete(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': args})

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Registration Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/observation/observationConfig.json")
    parser.add_argument('--port', help='default port', default=5001)
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    port = int(args.port)
    if not config_file:
        config_file = utils.get_parent_dir(__file__,2)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)

    api.add_resource(RoheRegistrationService, '/registration',resource_class_kwargs=configuration)
    app.run(debug=True, port=port)