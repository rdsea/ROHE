import qoa4ml.utils as utils
import sys, uuid, time, copy
import argparse
import pymongo
main_path = config_file = utils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.observation.metricCollector.roheAgenStreaming import RoheObservationAgent


from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)
local_agent_list = {}


class RoheObservationService(Resource):
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
    
    def show_agent(self):
        print("Agent: ", local_agent_list)
        for agent in local_agent_list:
            print(agent, "#####", local_agent_list[agent].status, local_agent_list[agent].insert_db)

    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})
    
    def post(self):
        response = {}
        if request.is_json:
            args = request.get_json(force=True)
            self.show_agent()
            if "application" in args:
                application_name = args["application"]
                app = self.get_app(application_name)
                if app == None:
                    response[application_name] = "Application {} not exist".format(application_name)
                else:
                    if "command" in args:
                        command = args["command"]
                        metadata = app
                        if command == "start":
                            if metadata["_id"] in local_agent_list:
                                agent = local_agent_list[metadata["_id"]]
                                if agent.status == 0:
                                    agent.start()
                                elif agent.status == 2:
                                    agent.restart()
                            else:
                                agent_config = metadata["agent_config"]
                                agent = RoheObservationAgent(agent_config)
                                local_agent_list[metadata["_id"]] = agent
                                agent.start()
                            self.show_agent()
                            response[application_name] = "Application agent for {} started ".format(application_name)
                        if command == "stop":
                            if metadata["_id"] in local_agent_list:
                                agent = local_agent_list[metadata["_id"]]
                                if agent.status != 2:
                                    agent.stop()
                                    self.show_agent()
                            response[application_name] = "Application agent for {} stopped ".format(application_name)
                        if command == "delete":
                            if metadata["_id"] in local_agent_list:
                                local_agent_list.pop(metadata["_id"])
                            self.collection.delete_many({"app_name":application_name})
                            response[application_name] = "Application agent for {} deleted ".format(application_name)

        return jsonify({'status': "success", "response":response})


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Mangement Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/observation/observationConfig.json")
    parser.add_argument('--port', help='default port', default=5010)
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    port = int(args.port)
    if not config_file:
        config_file = utils.get_parent_dir(__file__,2)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)
    api.add_resource(RoheObservationService, '/agent',resource_class_kwargs=configuration)
    app.run(debug=True, port=port)