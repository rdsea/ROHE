import qoa4ml.utils as utils
import sys, uuid, time, copy
import argparse
import pymongo
main_path = config_file = utils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.observation.metricCollector.roheAgenStreaming import RoheObservationAgent
from modules.roheObject import RoheObject

from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)
local_agent_list = {}


class RoheObservationService(Resource, RoheObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        # Init database connection
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.collection = self.db[self.db_config["collection"]]
        self.set_logger_level(int(self.conf["logging_level"]))

        # self.connector_config = self.conf["connector"]
        # self.collector_config = self.conf["collector"]
        
    
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

    def get(self):
        # Processing GET request
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})
    
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
    parser = argparse.ArgumentParser(description="Argument for Mangement Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/observation/observationConfig.json")
    parser.add_argument('--port', help='default port', default=5010)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    port = int(args.port)

    # load configuration file
    if not config_file:
        config_file = utils.get_parent_dir(__file__,2)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)
    
    # Run the Observation Service
    api.add_resource(RoheObservationService, '/agent',resource_class_kwargs=configuration)
    app.run(debug=True, port=port)