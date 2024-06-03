import copy
import logging
import time
import uuid

from flask import jsonify, request

from ..common.rest_service import RoheRestObject

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class RoheRegistration(RoheRestObject):
    def __init__(self, **kwargs) -> None:
        try:
            super().__init__()
            self.conf = kwargs

            # Init Database connection
            self.db_client = self.conf["db_client"]
            self.db_collection = self.conf["db_collection"]
            # Init default messageing connection
            self.connector_config = self.conf["connector_config"]
            self.collector_config = self.conf["collector_config"]
        except Exception as e:
            logging.error("Error in `__init__` RoheRegistration: {}".format(e))

    def get_app(self, application_name):
        """
        Get application configuration from database
        """
        try:
            query = [
                {"$sort": {"timestamp": 1}},
                {
                    "$group": {
                        "_id": "$appID",
                        "application_name": {"$last": "$application_name"},
                        "user_id": {"$last": "$user_id"},
                        "run_id": {"$last": "$run_id"},
                        "timestamp": {"$last": "$timestamp"},
                        "db": {"$last": "$db"},
                        "client_count": {"$last": "$client_count"},
                        "agent_config": {"$last": "$agent_config"},
                    }
                },
            ]
            app_list = list(self.db_client.get(self.db_collection, query))
            # Get application from application list
            for app in app_list:
                if app["application_name"] == application_name:
                    return app
            return None
        except Exception as e:
            logging.error("Error in `get_app` RoheRegistration: {}".format(e))
            return {}

    def update_app(self, metadata):
        """
        Update application configuration
        """
        try:
            return self.db_client.insert_one(self.db_collection, metadata)
        except Exception as e:
            logging.error("Error in `update_app` RoheRegistration: {}".format(e))
            return {}

    def generate_agent_conf(self, metadata) -> dict:
        try:
            # Database configuration
            agent_db_config = copy.deepcopy(self.db_collection)
            agent_db_config.database = (
                "application_" + metadata["application_name"] + "_" + metadata["appID"]
            )
            agent_db_config.collection = "metric_collection_" + metadata["run_id"]
            # Collector configuration
            collector = copy.deepcopy(self.collector_config)
            i_config = collector.config
            i_config["exchange_name"] = str(metadata["application_name"]) + "_exchange"
            i_config["in_routing_key"] = str(metadata["application_name"]) + ".#"
            agent_config = {}
            agent_config["db_authentication"] = self.db_client.to_dict()
            agent_config["db_collection"] = agent_db_config.dict()
            agent_config["collector"] = collector.dict()
            return agent_config
        except Exception as e:
            logging.error(
                "Error in `generate_agent_conf` RoheRegistration: {}".format(e)
            )
            return {}

    def register_app(self, application_name, run_id, user_id) -> dict:
        try:
            # Create new application configuration and push to database
            metadata = {}
            metadata["application_name"] = application_name
            metadata["run_id"] = run_id
            metadata["user_id"] = user_id
            metadata["appID"] = str(uuid.uuid4())
            metadata["db"] = "application_" + application_name + "_" + metadata["appID"]
            metadata["timestamp"] = time.time()
            metadata["client_count"] = 1
            metadata["agent_config"] = self.generate_agent_conf(metadata)
            self.db_client.insert_one(self.db_collection, metadata)
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
                if "application_name" in args:
                    application_name = args["application_name"]
                    run_id = args["run_id"]
                    user_id = args["user_id"]

                    # look up for app in database
                    app = self.get_app(application_name)

                    # if not found - create new app
                    if app is None:
                        metadata = self.register_app(application_name, run_id, user_id)
                        response[application_name] = (
                            "Application {} created for user {} with run ID: {}".format(
                                application_name, user_id, run_id
                            )
                        )
                    # if app is found - update the existing app
                    else:
                        response[application_name] = "Application already exist"
                        metadata = app
                        metadata["client_count"] += 1
                        metadata["timestamp"] = time.time()
                        metadata["appID"] = copy.deepcopy(metadata["_id"])
                        metadata.pop("_id")
                        self.update_app(metadata)

                    # TO DO
                    # Check user_id, role, stage_id, instance_id

                    # Prepare connector for QoA Client
                    connector = copy.deepcopy(self.connector_config)
                    i_config = connector.config
                    i_config["exchange_name"] = str(application_name) + "_exchange"
                    i_config["out_routing_key"] = str(application_name)
                    if "user_id" in args:
                        i_config["out_routing_key"] = (
                            i_config["out_routing_key"] + "." + args["user_id"]
                        )
                    if "stage_id" in args:
                        i_config["out_routing_key"] = (
                            i_config["out_routing_key"] + "." + args["stage_id"]
                        )
                    if "instance_id" in args:
                        i_config["out_routing_key"] = (
                            i_config["out_routing_key"] + "." + args["instance_id"]
                        )
                    i_config["out_routing_key"] = (
                        i_config["out_routing_key"]
                        + ".client"
                        + str(metadata["client_count"])
                    )

                    response["appID"] = metadata["appID"]
                    response["connector"] = connector.to_qoa4ml_config()
                else:
                    response["Error"] = "Application name not found"

            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logging.error("Error in `post` RoheRegistration: {}".format(e))
            return jsonify({"status": "request fail"})
