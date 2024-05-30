import json

# from app.object_classification.lib.roheService import RoheRestObject
from core.common.restService import RoheRestObject
from flask import request

from app.object_classification.services.aggregating.aggregatingServiceExecutor import (
    AggregatingServiceExecutor,
)

# import app.object_classification.modules.utils as pipeline_utils


class AggregatingServiceController(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        self.aggregating_service_executor: AggregatingServiceExecutor = self.conf[
            "aggregating_service_executor"
        ]
        print(f"\n\nThis is my executor: {self.aggregating_service_executor}")
        log_lev = self.conf.get("log_lev", 2)
        self.set_logger_level(logging_level=log_lev)

        self.post_command_handlers = {
            "change_aggregating_function": self._handle_change_aggregating_function,
        }

    def get(self):
        """
        return message to client to notify them that they are accessing the correct ingestion server
        """
        response = "This is aggregating service controller"
        return (
            json.dumps({"response": response}),
            200,
            {"Content-Type": "application/json"},
        )

    def post(self):
        """
        Handles POST requests for the inference service.
        """
        try:
            command = request.form.get("command")
            handler = self.post_command_handlers.get(command)

            if handler:
                success, response = handler(request)
                if success:
                    status_code = 200
                else:
                    status_code = 404
                result = (
                    json.dumps({"response": response}),
                    status_code,
                    {"Content-Type": "application/json"},
                )
            else:
                result = (
                    json.dumps({"response": "Command not found"}),
                    404,
                    {"Content-Type": "application/json"},
                )

        except Exception as e:
            result = (
                json.dumps({"error": str(e)}),
                500,
                {"Content-Type": "application/json"},
            )

        return result

    def _handle_change_aggregating_function(self, request):
        new_func = request.form.get("new_func")
        success = self.aggregating_service_executor.change_aggregating_function(
            func_name=new_func
        )
        if success:
            response = (
                f"Successfully change image info service url of the processing service"
            )
        else:
            response = f"Something went wrong"
        return success, response
