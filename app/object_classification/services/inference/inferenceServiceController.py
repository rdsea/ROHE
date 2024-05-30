import json
import os

from core.common.restService import RoheRestObject
from flask import request

import app.object_classification.modules.utils as pipeline_utils
from app.object_classification.lib.connectors.storage.minioStorageConnector import (
    MinioConnector,
)
from app.object_classification.modules.common import InferenceEnsembleState
from app.object_classification.modules.objectClassificationAgent import (
    ObjectClassificationAgent,
)


class InferenceServiceController(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        log_lev = self.conf.get("log_lev", 2)
        self.set_logger_level(logging_level=log_lev)

        self.post_command_handlers = {
            "load_new_weights": self._handle_load_new_weights_req,
            "load_new_model": self._handle_load_new_model_req,
            "change_ensemble_mode": self._handle_change_ensemble_mode,
        }

        # ML agent
        self.MLAgent: ObjectClassificationAgent = self.conf["MLAgent"]
        # variable control whether to send inference result to mongodb server or to kafka topic
        self.ensemble_mode: InferenceEnsembleState = self.conf["ensemble_controller"]

    def get(self):
        """
        return message to client to notify them that they are accessing the correct server
        """
        response = "This is service controller of the inference service"
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

    def _handle_load_new_weights_req(self, request: request):
        local_file = request.form.get("local_file")
        if local_file:
            return self._handle_load_new_local_weights_req(request)
        # else:
        #     return self._handle_load_new_remote_weights_req(request)

    def _handle_load_new_local_weights_req(self, request: request):
        local_file_path = request.form.get("weights_url")
        try:
            with self.model_lock:
                self.MLAgent.load_weights(local_file_path)
        # after loading the weight, delete the local file
        except:
            os.remove(local_file_path)
            return "fail to update new weights (layers doesn't match)"

        os.remove(local_file_path)
        return "successfully update new weights"

    # def _handle_load_new_remote_weights_req(self, request: request):
    #     remote_file_path = request.form.get('weights_url')
    #     local_file_path = './tmp_weights_file.h5'
    #     success = self.minio_connector.download(remote_file_path= remote_file_path,
    #                                                      local_file_path= local_file_path)
    #     if success:
    #         try:
    #             with self.model_lock:
    #                 self.MLAgent.load_weights(local_file_path)
    #         # after loading the weight, delete the local file
    #         except:
    #             os.remove(local_file_path)
    #             return "fail to update new weights (layers doesn't match)"

    #         os.remove(local_file_path)
    #         return "successfully update new weights"
    #     else:
    #         return "cannot download the files"

    # payload = {
    #     'command': 'modify_weights',
    #     'local_file': True,
    #     'weights_url': 'weight-file-name.h5',
    #     'architecture_url': 'architecture-file-name.json'
    # }
    # # Send POST request
    # response = requests.post('http://server-address/api-name', json=payload)
    def _handle_load_new_model_req(self, request: request):
        local_file = request.form.get("local_file")
        if local_file:
            return self._handle_load_new_local_model_req(request)
        # else:
        #     return self._handle_load_new_remote_model_req(request)

    def _handle_change_ensemble_mode(self, request: request):
        try:
            ensemble_mode = request.form.get("ensemble_mode")
            # ensemble_mode = request.form.get('ensemble_mode')
            ensemble_mode = ensemble_mode.lower() == "true"

            # ensemble_mode= bool(request.form.get('ensemble_mode'))
            print(f"\n\n\n\nThis is the request ensemble mode: {ensemble_mode}")
            message = f"Successfully change the ensemble mode from {self.ensemble_controller.ensemble_modee()} to {ensemble_mode}"
            with self.model_lock:
                print(
                    f"Mode before changing: {self.ensemble_controller.ensemble_modee()}"
                )
                self.ensemble_controller.ensemble_modee(ensemble_mode)
                # print(f"The current ensemble mode after making request: {self.ensemble_controller.ensemble_modee()}\n\n\n")
                print(
                    f"Mode after changing: {self.ensemble_controller.ensemble_modee()}"
                )

            return message

        except Exception as e:
            return f"Local model case. Failed to update new weights or architecture: {str(e)}"

    # def _get_ensemble_mode(self) -> bool:
    #     return self.ensemble
    # def _change_ensemble_mode(self, mode: bool):
    #     self.ensemble = mode

    def _handle_load_new_local_model_req(self, request: request):
        try:
            # print (request.form.get('weights_url'))
            # files = {
            #     "weights_file": request.form.get('weights_url'),
            #     "architecture_file": request.form.get('architecture_url')
            # }
            chosen_model_id: str = request.form.get("model_id")
            files = self.MLAgent.get_model_files(chosen_model_id)
            # files = {
            #     "weights_file": request.form.get('weights_url'),
            #     "architecture_file": request.form.get('architecture_url')
            # }

            new_model = self.MLAgent.load_model_from_config(**files)

            with self.model_lock:
                self.MLAgent.change_model(new_model)
                self.MLAgent.set_model_id(chosen_model_id)
                print(
                    f"\n\n\nThis is the current model id: {self.MLAgent.get_model_id()}"
                )

            return "Local file case. Sucessfully change the model"

        except Exception as e:
            return f"Local model case. Failed to update new weights or architecture: {str(e)}"

    # def _handle_load_new_remote_model_req(self, request: request):
    #     # Download weights file
    #     weight_remote_file_path = request.form.get('weights_url')
    #     weight_local_file_path = './tmp_weights_file.h5'
    #     success = self.minio_connector.download(remote_file_path=weight_remote_file_path,
    #                                                 local_file_path=weight_local_file_path)
    #     if not success:
    #         return "cannot download the weights file"
    #     # Download architecture file
    #     architecture_remote_file_path = request.form.get('architecture_url')
    #     architecture_local_file_path = './tmp_architecture_file.json'
    #     success = self.minio_connector.download(remote_file_path=architecture_remote_file_path,
    #                                                     local_file_path=architecture_local_file_path)
    #     if success:
    #         try:
    #             files = {
    #                 "architecture_file": architecture_local_file_path,
    #                 "weights_file": weight_local_file_path
    #             }
    #             new_model = self.MLAgent.load_model(files= files)
    #             with self.model_lock:
    #                 self.MLAgent.change_model(new_model)

    #             # Cleanup
    #             os.remove(weight_local_file_path)
    #             os.remove(architecture_local_file_path)

    #             return "Remote case. Successfully change the model"

    #         except Exception as e:
    #             # Cleanup and return failure
    #             os.remove(weight_local_file_path)
    #             os.remove(architecture_local_file_path)
    #             return f"Failed to update new weights or architecture: {str(e)}"

    #     else:
    #         return "cannot download the json file"

    # this function is for the situation when the minio server change (when scaling)
    # now, focus on implementation a fixed one first
    # def download_minio_weights_file(minio_config, url):
    #     pass

    # def _retrieve_image(self, binary_encoded, dtype):
    #     try:
    #         image = np.frombuffer(binary_encoded.read(), dtype=dtype)
    #         image = image.reshape(self.MLAgent.input_shape)
    #     except:
    #         image = None
    #     return image
