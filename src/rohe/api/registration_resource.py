import copy
import time

from flask import jsonify, request
from flask_restful import Resource
from qoa4ml.config.configs import (
    AMQPConnectorConfig,
)

from ..common.data_models import RegistrationRequest
from ..common.logger import logger
from ..observation.registration_manager import RegistrationManager


class RegistrationResource(Resource):
    def __init__(self, **kwargs) -> None:
        self.config = kwargs
        self.registration_manager: RegistrationManager = self.config[
            "registration_manager"
        ]

    def post(self):
        try:
            # Function to handle POST request
            if not request.is_json:
                return jsonify(
                    {"status": "failed", "response": "Currently only accept json"}
                )
            response = {}
            try:
                registration_data = RegistrationRequest.model_validate_json(
                    request.data
                )
            except Exception:
                response["Error"] = (
                    "Incorrect request, the correct should have 3 fields: application_name, run_id, user_id"
                )
                return jsonify({"status": "success", "response": response})

            # parse app metadata
            application_name = registration_data.application_name
            run_id = registration_data.run_id
            user_id = registration_data.user_id

            # look up for app in database
            app = self.registration_manager.get_app(application_name)

            # if not found - create new app
            if app is None:
                metadata = self.registration_manager.register_app(
                    application_name, run_id, user_id
                )
                response[application_name] = (
                    f"Application {application_name} created for user {user_id} with run ID: {run_id}"
                )
            # if app is found - update the existing app
            else:
                response[application_name] = "Application already exist"
                metadata = app
                metadata["client_count"] += 1
                metadata["timestamp"] = time.time()
                metadata["app_id"] = copy.deepcopy(metadata["_id"])
                metadata.pop("_id")
                self.registration_manager.update_app(metadata)

            # TO DO
            # Check user_id, role, stage_id, instance_id

            # Prepare connector for QoA Client
            connector = copy.deepcopy(self.registration_manager.connector_config)
            i_config = connector.config
            if isinstance(i_config, AMQPConnectorConfig):
                i_config.exchange_name = str(application_name) + "_exchange"
                i_config.out_routing_key = str(application_name)
                if registration_data.user_id is not None:
                    i_config.out_routing_key = (
                        i_config.out_routing_key + "." + registration_data.user_id
                    )
                if registration_data.stage_id is not None:
                    i_config.out_routing_key = (
                        i_config.out_routing_key + "." + registration_data.stage_id
                    )
                if registration_data.instance_id is not None:
                    i_config.out_routing_key = (
                        i_config.out_routing_key + "." + registration_data.instance_id
                    )
                i_config.out_routing_key = (
                    i_config.out_routing_key + ".client" + str(metadata["client_count"])
                )

                response["app_id"] = metadata["app_id"]
                response["connector"] = connector.model_dump()

            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logger.exception(f"Error in `post` RoheRegistration: {e}")
            return jsonify({"status": "request fail"})

    def delete(self):
        try:
            if not request.is_json:
                return jsonify(
                    {"status": "failed", "response": "Currently only accept json"}
                )
            response = {}
            try:
                registration_data = RegistrationRequest.model_validate_json(
                    request.data
                )
            except Exception:
                response["Error"] = (
                    "Incorrect request, the correct should have 3 fields: application_name, run_id, user_id"
                )
                return jsonify({"status": "success", "response": response})
            application_name = registration_data.application_name
            run_id = registration_data.run_id
            user_id = registration_data.user_id
            self.registration_manager.delete_app(application_name, run_id, user_id)
            return jsonify(
                {"status": "success", "response": f"Deleted {application_name}"}
            )
        except Exception as e:
            logger.exception(f"Error in `delete` RoheRegistration: {e}")
            return jsonify({"status": "request fail"})
