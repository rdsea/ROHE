from flask import jsonify, request
from flask_restful import Resource

from ..common.data_models import AddNodeRequest, AddServiceRequest, RemoveNodeRequest
from ..common.logger import logger


class OrchestationResource(Resource):
    def __init__(self, **kwargs) -> None:
        self.node_and_service_manager = kwargs["node_and_service_manager"]

    def get(self):
        try:
            args = request.query_string.decode("utf-8").split("&")
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logger.exception(f"Error in `get_nodes` RoheNodeAndServiceManager: {e}")
            return jsonify({"status": "unsupported"})

    def post(self, command: str):
        try:
            if not request.is_json:
                response = {"result": "only support json type"}
            response = {}
            if command == "add-node":
                node_data = AddNodeRequest.model_validate_json(request.data)
                response = self.node_and_service_manager.add_nodes(node_data.data)

            if command == "remove-all-nodes":
                self.node_and_service_manager.db_client.drop(
                    self.node_and_service_manager.node_collection
                )
                response = {"result": "All nodes removed"}

            if command == "remove-node":
                remove_node_data = RemoveNodeRequest.model_validate_json(request.data)
                response = self.node_and_service_manager.remove_nodes(
                    remove_node_data.data
                )

            if command == "add-service":
                service_data = AddServiceRequest.model_validate_json(request.data)
                response = self.node_and_service_manager.add_services(service_data.data)

            if command == "remove-all-services":
                self.node_and_service_manager.db_client.drop(
                    self.node_and_service_manager.service_collection
                )
                response = {"result": "All services removed"}

            # TODO: improve this, the body is too big now
            if command == "remove-service":
                pass
                # response = self.remove_services(args["data"])

            if command == "get-all-services":
                response = {"result": self.node_and_service_manager.get_services()}

            if command == "get-all-nodes":
                response = {"result": self.node_and_service_manager.get_nodes()}

            if command == "start-agent":
                self.node_and_service_manager.orchestration_agent.start()
                response = {"result": "Agent started"}

            if command == "stop-agent":
                self.node_and_service_manager.orchestration_agent.stop()
                response = {"result": "Agent Stop"}

            if not response:
                response = {"result": "Unknown command"}
            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logger.exception(f"Error in `get_nodes` RoheNodeAndServiceManager: {e}")
            return jsonify({"status": "fail"})

    def put(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logger.exception(f"Error in `get_nodes` RoheNodeAndServiceManager: {e}")
            return jsonify({"status": "unsupported"})

    def delete(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logger.exception(f"Error in `get_nodes` RoheNodeAndServiceManager: {e}")
            return jsonify({"status": "unsupported"})
