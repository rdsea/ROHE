# import os, sys

import json
from threading import Lock
from typing import Dict, Optional, Tuple

import numpy as np
from core.common.restService import RoheRestObject
from flask import request
from qoa4ml.QoaClient import QoaClient

import app.object_classification.modules.utils as pipeline_utils
from app.object_classification.lib.connectors.quixStream import QuixStreamProducer

# from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
from app.object_classification.lib.connectors.storage.mongoDBConnector import (
    MongoDBConnector,
)
from app.object_classification.modules.common import InferenceEnsembleState
from app.object_classification.modules.objectClassificationAgent import (
    ObjectClassificationAgent,
)


class InferenceServiceExecutor(RoheRestObject):
    """ """

    def __init__(self, **kwargs):
        self.conf = kwargs
        log_lev = self.conf.get("log_lev", 2)
        super().__init__(log_level=log_lev)

        if "qoaClient" in self.conf:
            print(f"There is qoa service enable in the server")
            self.qoaClient: QoaClient = self.conf["qoaClient"]
            print(f"This is qoa client: {self.qoaClient}")
        else:
            self.qoaClient = None

        # the pipeline id should be configured
        self.pipeline_id: str = self.conf["pipeline_id"]

        ############################################################################################################################################
        # The REST AGENT should not manage ML model. We should separate REST and ML -> Use classificationObject in module to manage ML models
        # for example:
        # self.MLAgent = ObjectClassificationAgent()
        ############################################################################################################################################

        # model lock
        self.model_lock: Lock = self.conf["model_lock"]
        # ML agent
        self.MLAgent: ObjectClassificationAgent = self.conf["MLAgent"]

        # variable control whether to send inference result to mongodb server or to kafka topic
        self.ensemble_mode: InferenceEnsembleState = self.conf["ensemble_controller"]
        self.ensemble_lock: Lock = self.conf["ensemble_lock"]

        # print(f"This is the current ensemble mode: {self.ensemble_mode.get_mode()}")
        # initialized both
        # to be flexible to switch mode
        # between send result to either kafka topic
        # or send to mongodb
        self.quix_producer: QuixStreamProducer = self.conf["quix_producer"]
        self.mongo_connector: MongoDBConnector = self.conf["mongo_connector"]

    def get(self):
        try:
            response = f"This is Object Classification Server. Current model in use: {self.MLAgent.get_model_id()} \n The only accepted input shape: {self.MLAgent.input_shape}"
            return (
                json.dumps({"response": response}),
                200,
                {"Content-Type": "application/json"},
            )
        except Exception as e:
            print("Exception:", e)
            return (
                json.dumps({"error": "An error occurred"}),
                500,
                {"Content-Type": "application/json"},
            )

    def post(self):
        """
        Handles POST requests for the inference service (prediction request from client).
        get an image attached from the request and returns a dictionary as prediction result.
        """
        if self.qoaClient:
            self.qoaClient.timer()

        try:
            response, inference_result = self._handle_predict_req(request)
            print(
                f"\n\n\nThis is the response and inference result: {response}, {inference_result}"
            )
            if self.qoaClient:
                self.qoaClient.timer()

            if inference_result is None:
                result = (
                    json.dumps({"response": response, "inference_result": None}),
                    404,
                    {"Content-Type": "application/json"},
                )
            else:
                result = (
                    json.dumps(
                        {"response": response, "inference_result": inference_result}
                    ),
                    200,
                    {"Content-Type": "application/json"},
                )

        except Exception as e:
            print("Exception:", e)
            result = (
                json.dumps({"error": "An error occurred"}),
                500,
                {"Content-Type": "application/json"},
            )

        # qoa4ml service
        if self.qoaClient:
            try:
                if inference_result is None:
                    confidence = None
                else:
                    confidence = float(inference_result["confidence_level"])

                self.qoaClient.observeInferenceMetric("confidence", confidence)
                report = self.qoaClient.report(submit=True)

            except Exception as e:
                print(e)

        return result

    def _handle_predict_req(self, request: request) -> Tuple[str, dict]:
        """
        sample request
            # Convert the numpy array to bytes
            image_bytes = image_np.tobytes()

            # Metadata and command
            metadata = {'shape': '32,32,3', 'dtype': str(image_np.dtype)}
            payload = {'metadata': json.dumps(metadata)}

            files = {'image': ('image', image_bytes, 'application/octet-stream')}
            requests.post('http://server-address:port/api-name', data=payload, files=files)
        """

        inference_result = None
        ### METADATA ####
        metadata = self._get_image_metadata(request=request)
        if metadata is None:
            response = f"There is no metadata with this request. Cannot retrieve the image for the inference stage"
            return response, inference_result
        try:
            request_input_shape = pipeline_utils.convert_str_to_tuple(metadata["shape"])
        except:
            response = f"metadata of the image is wrong."
            return response, inference_result

        if self.qoaClient:
            self.qoaClient.observeMetric("image_width", request_input_shape[0], 1)
            self.qoaClient.observeMetric("image_height", request_input_shape[1], 1)
            model_metadata = self.MLAgent.get_model_metadata()
            for attribute, value in model_metadata.items():
                self.qoaClient.observeInferenceMetric(attribute, value)

        model_input_shape = self.MLAgent.get_input_shape()
        matched_dim = request_input_shape == model_input_shape

        if not matched_dim:
            response = f"Image shape is not matched with the input shape of the model {model_input_shape}"
            return response, inference_result

        try:
            dtype = metadata["dtype"]
            binary_encoded = request.files["image"].read()
        except:
            response = f"There is no binary image attached to the request or there is no specification of dtype or both"
            return response, inference_result

        # Convert the binary data to a numpy array and decode the image
        # print(f"This is binary encoded image type: {type(binary_encoded)}")
        # print(f"This is dtype: {dtype}")
        # print(f"This is shape: {model_input_shape}")

        image = pipeline_utils.decode_binary_image(
            binary_encoded, dtype, shape=model_input_shape
        )
        if image is None:
            response = "something wrong with the retrieving image process"
            return response, inference_result
        try:
            with self.model_lock:
                inference_result = self.MLAgent.predict(image)
        except:
            response = "something wrong with the model"
            return response, inference_result

        if inference_result is None:
            response = "ML model fail to make prediction"
            return response, inference_result

        # send the inference result to appropriate channel base on the ensemble config
        self._publish_inference_result(
            request_info=metadata, inference_result=inference_result
        )
        response = f"Success to make inference prediction from the image"
        return response, inference_result

    def _publish_inference_result(self, request_info: dict, inference_result: dict):
        """"""
        message = self._generate_publish_message(request_info, inference_result)
        # if self.ensemble == True:
        with self.ensemble_lock:
            mode = self.ensemble_mode.get_mode() == True

        print(
            f"\n\n The mode when forwarding result: {mode}, the mode of ensemble state: {self.ensemble_mode.get_mode()}"
        )
        if mode:
            print(f"mode when entering kafka: {mode}")
            # print("About to send message to kafka topic")
            self.quix_producer.produce_values(message=message)
            # print(f"\n\n\npost success")

        else:
            print(f"mode when entering mongo: {mode}")
            # print(f"This is the published data: {message}, and its type: {type(message)}")
            # Use the upload method to upload the data
            try:
                self.mongo_connector.upload([message])
                print("Data uploaded successfully.")
            except Exception as e:
                print(f"Failed to upload data. Error: {e}")

    def _generate_publish_message(
        self, request_info: dict, inference_result: dict
    ) -> Dict[str, str]:
        """"""
        print(f"\n\n\n This is the inference results: {inference_result}")
        pred = inference_result["prediction"]
        # print(f"\n\n\n\n\n\n This is the type of the prediction: {type(pred)}\n\n")

        ### METADATA ####
        message = {
            "request_id": request_info["request_id"],
            "pipeline_id": self.pipeline_id,
            "inference_model_id": self.MLAgent.get_model_id(),
            "prediction": pred,
        }

        # if self.ensemble:
        if self.ensemble_mode.get_mode() == True:
            message = self._proccess_message_for_ensemble(message=message)

        print(f"This is the message: {message}\n\n\n")
        return message

    def _proccess_message_for_ensemble(self, message):
        message["prediction"] = np.array(message["prediction"]).tobytes()
        return message

    def _get_image_metadata(self, request) -> Optional[Dict]:
        try:
            metadata_json = request.form.get("metadata")
            if metadata_json is None:
                return None
            metadata = json.loads(metadata_json)
            return metadata
        except json.JSONDecodeError:
            return None
