import sys, uuid, time, copy
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib.rohe.restService import RoheRestObject
import logging
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)
from flask import jsonify, request


class RoheRegistration(RoheRestObject):
    def __init__(self, **kwargs) -> None:
        try:
            super().__init__()
            self.conf = kwargs
            
            # Init Database connection
            self.dbClient = self.conf["dbClient"]
            self.dbCollection = self.conf["dbCollection"]
            # Init default messageing connection
            self.connectorConf = self.conf["connectorConfig"]
            self.collectorConf = self.conf["collectorConfig"]
        except Exception as e:
            logging.error("Error in `__init__` RoheRegistration: {}".format(e))
            return {}
    
    def get_app(self,appName):
        try:
            # Get application configuration from database
            # Prepare query pipeline
            pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "appName": {"$last": "$appName"},"userID": {"$last": "$userID"}, "runID": {"$last": "$runID"}, "timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
            app_list = list(self.dbClient.get(self.dbCollection,pipeline))
            # Get application from application list
            for app in app_list:
                if app["appName"] == appName:
                    return app
            return None
        except Exception as e:
            logging.error("Error in `get_app` RoheRegistration: {}".format(e))
            return {}
    
    def update_app(self,metadata):
        try:
            # update application configuration
            return self.dbClient.insert_one(self.dbCollection, metadata)
        except Exception as e:
            logging.error("Error in `update_app` RoheRegistration: {}".format(e))
            return {}

    def generate_agent_conf(self, metadata) -> dict:
        try:
            # Database configuration
            agent_db_config = copy.deepcopy(self.dbCollection)
            agent_db_config.database = "application_"+metadata["appName"]+"_"+metadata["appID"]
            agent_db_config.collection = "metric_collection_"+metadata["runID"]
            # Collector configuration
            collector = copy.deepcopy(self.collectorConf)
            i_config = collector.config
            i_config["exchange_name"] = str(metadata["appName"])+"_exchange"
            i_config["in_routing_key"] = str(metadata["appName"])+".#"
            agent_config ={}
            agent_config["db_authentication"] = self.dbClient.to_dict()
            agent_config["db_collection"] = agent_db_config.dict()
            agent_config["collector"] = collector.dict()
            return agent_config
        except Exception as e:
            logging.error("Error in `generate_agent_conf` RoheRegistration: {}".format(e))
            return {}
    
    def register_app(self,appName, runID, userID) -> dict:
        try:
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
            self.dbClient.insert_one(self.dbCollection, metadata)
            return metadata
        except Exception as e:
            logging.error("Error in `register_app` RoheRegistration: {}".format(e))
            return {}
    

    def post(self):
        try:
            # Functon to handle POST request
            if request.is_json:
                args = request.get_json(force=True)
                response = {}
                # parse app metadata
                if "appName" in args:
                    appName = args["appName"]
                    runID = args["runID"]
                    userID = args["userID"]

                    # look up for app in database
                    app = self.get_app(appName)

                    # if not found - create new app
                    if app == None:
                        metadata = self.register_app(appName, runID, userID)
                        response[appName] = "Application {} created for user {} with run ID: {}".format(appName, userID, runID)
                    # if app is found - update the existing app
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
                    connector = copy.deepcopy(self.connectorConf)
                    i_config = connector.config
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
                    response["connector"] = connector.to_qoa4ml_config()
                else:
                    response["Error"] = "Application name not found"
                
            return jsonify({'status': "success", "response":response})
        except Exception as e:
            logging.error("Error in `post` RoheRegistration: {}".format(e))
            return jsonify({'status': "request fail"})