import json

from core.common.restService import RoheRestObject
from flask import request

import app.object_classification.modules.utils as pipeline_utils
from app.object_classification.services.processing.processingServiceExecutor import (
    ProcessingServiceExecutor,
)


class ProcessingServiceController(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        self.processing_service_executor: ProcessingServiceExecutor = self.conf[
            "processing_service_executor"
        ]
        print(f"\n\nThis is my executor: {self.processing_service_executor}")
        log_lev = self.conf.get("log_lev", 2)
        self.set_logger_level(logging_level=log_lev)

        self.post_command_handlers = {
            "change_image_info_service_url": self._handle_change_image_info_service_url,
            "change_inference_service_urls": self._handle_change_inference_service_urls,
            "change_image_processing_function": self._handle_change_image_processing_function,
        }

    def get(self):
        """
        return message to client to notify them that they are accessing the correct ingestion server
        """
        response = "This is processing service controller"
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

    def _handle_change_image_info_service_url(self, request):
        new_url = request.form.get("url")
        success = self.processing_service_executor.change_image_info_service_url(
            url=new_url
        )
        if success:
            response = (
                f"Successfully change image info service url of the processing service"
            )
        else:
            response = f"Something went wrong"
        return success, response

    def _handle_change_inference_service_urls(self, request):
        new_urls = request.form.get("urls")
        new_urls = pipeline_utils.convert_str_to_tuple(new_urls)
        success = self.processing_service_executor.change_inference_service_url(
            new_urls
        )
        if success:
            response = (
                f"Successfully change inference service urls of the processing service"
            )
        else:
            response = f"Something went wrong"

        return success, response

    def _handle_change_image_processing_function(self, request):
        new_func_name = request.form.get("func_name")
        success = self.processing_service_executor.change_image_processing_function(
            func_name=new_func_name
        )
        if success:
            response = f"Successfully change image processing function of the processing service"
        else:
            response = f"Something went wrong"
        return success, response
