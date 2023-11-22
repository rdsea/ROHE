import os, sys

import json
import numpy as np
from flask import request
from typing import Dict, Optional


from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
from app.object_classification.lib.connectors.storage.mongoDBConnector import MongoDBConnector
from app.object_classification.lib.connectors.quixStream import QuixStreamProducer

from app.object_classification.modules.objectClassificationAgent import ObjectClassificationAgent
from app.object_classification.modules.common import InferenceEnsembleState
import app.object_classification.modules.utils as pipeline_utils

from lib.rohe.restService import RoheRestObject

from qoa4ml.QoaClient import QoaClient

    
# class ClassificationRestService():
class InferenceServiceExecutor(RoheRestObject):
    '''
    '''
    def __init__(self, **kwargs):
        self.conf = kwargs
        log_lev = self.conf.get('log_lev', 2)
        super().__init__(log_level= log_lev)

        if 'qoaClient' in self.conf:
            print(f"There is qoa service enable in the server")
            self.qoaClient: QoaClient = self.conf['qoaClient']
        else:
            self.qoaClient = None

        # the pipeline id should be configured
        # self.pipeline_id: str = self.conf.get('pipeline_id') or "pipeline_sample"
        self.pipeline_id: str = self.conf['pipeline_id']


        ############################################################################################################################################
        # The REST AGENT should not manage ML model. We should separate REST and ML -> Use classificationObject in module to manage ML models
        # for example:
        # self.MLAgent = ObjectClassificationAgent()
        ############################################################################################################################################

        # ML agent
        self.MLAgent: ObjectClassificationAgent = self.conf['MLAgent']

        # variable control whether to send inference result to mongodb server or to kafka topic
        self.ensemble_mode: InferenceEnsembleState = self.conf['ensemble_controller']
        # print(f"This is the current ensemble mode: {self.ensemble_mode.get_mode()}")
        # initialized both
        # to be flexible to switch mode 
        # between send result to either kafka topic
        # or send to mongodb 

        self.quix_producer: QuixStreamProducer = self.conf['quix_producer'] 
        self.mongo_connector: MongoDBConnector = self.conf['mongo_connector'] 
        
        # set model lock
        self.model_lock = self.conf['lock']


    def get(self):
        try:
            response = f"This is Object Classification Server. \n The input shape: {self.MLAgent.input_shape}"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def post(self):
        """
        Handles POST requests for the inference service (prediction request from client).
        # Command Descriptions:
        # - predict: get an image attached from the request and returns a prediction.
        """
        if self.qoaClient:
            self.qoaClient.timer() 
        try:
            # command = request.form.get('command')
            # handler = self.post_command_handlers.get(command)

            # if handler:
            #     response = handler(request)
            response = self._handle_predict_req(request)
            if self.qoaClient:
                self.qoaClient.timer()
                
            result = json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
            # else:
            #     result = json.dumps({"response": "Command not found"}), 404, {'Content-Type': 'application/json'}
            
        except Exception as e:
            print("Exception:", e)
            result = json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}
        
        if self.qoaClient:
            self.qoaClient.timer() 
        # if command == "predict":
        try:
            if self.qoaClient:
                self.qoaClient.observeInferenceMetric("confidence", float(response['confidence_level']))
        except Exception as e:
            print(e)

        if self.qoaClient:
            report = self.qoaClient.report(submit=True)
#             print(report)


        return result


    # # Convert the numpy array to bytes
    # image_bytes = image_np.tobytes()
    # # Metadata and command
    # metadata = {'shape': '32,32,3', 'dtype': str(image_np.dtype)}
    # payload = {'command': 'predict', 'metadata': json.dumps(metadata)}
    # files = {'image': ('image', image_bytes, 'application/octet-stream')}
    # requests.post('http://server-address/api-name', data=payload, files=files)
    def _handle_predict_req(self, request: request):
        metadata = self._get_image_meta_data(request= request)
        matched_dim = self._check_dim(metadata= metadata)
        if matched_dim:
            dtype = metadata['dtype']
            binary_encoded = request.files['image']
            # Convert the binary data to a numpy array and decode the image
            image = pipeline_utils.decode_binary_image(binary_encoded, dtype)
            if image is not None:
                try:
                    with self.model_lock:
                        result = self.MLAgent.predict(image)
                        # a function here to either publish to kafka topic
                        # or write data to mongodb server
                        self._publish_predict_request(request_info= metadata, prediction= result)
                        return result
                except:
                    return "something wrong with the model"
            else:
                return "something wrong with the retrieving image process"
        else:
            return f"Image shape is not matched with the input shape of the model {self.MLAgent.input_shape} "
            
    def _publish_predict_request(self, request_info, prediction):
        message = self._generate_publish_message(request_info, prediction)
        # if self.ensemble == True:
        mode = self.ensemble_controller.ensemble_modee() == True
        print(f"\n\n The mode when forwarding result: {mode}, the mode of ensemble state: {self.ensemble_controller.ensemble_modee()}")
        if mode:
            print(f"mode when entering kafka: {mode}")
            # print("About to send message to kafka topic")
            self.kafka_producer.produce_values(message= message)
        else:
            print(f"mode when entering mongo: {mode}")
            # print("About to publish to mongodb")
            # print(f"This is the published data: {message}, and its type: {type(message)}")
            # Use the upload method to upload the data
            try:
                self.mongo_connector.upload([message])
                print('Data uploaded successfully.')
            except Exception as e:
                print(f'Failed to upload data. Error: {e}')

    def _generate_publish_message(self, request_info, prediction) -> Dict[str, str]:
        print(f"\n\n\n This is the prediction: {prediction}")
        pred = prediction["prediction"]
        # print(f"\n\n\n\n\n\n This is the type of the prediction: {type(pred)}\n\n")

        ### METADATA ####
        message = {
            "request_id": request_info['request_id'],
            "prediction": pred,
            "pipeline_id": self.pipeline_id,
            "inference_model_id": self.MLAgent.get_model_id(),
        }
        # if self.ensemble:
        if self.ensemble_controller.ensemble_modee() == True:
            message = self._proccess_message_for_ensemble(message= message)

        print(f"This is the message: {message}\n\n\n")
        return message
    
    def _proccess_message_for_ensemble(self, message):
        message['prediction'] = np.array(message['prediction'])
        return message
    
    def _check_dim(self, metadata) -> bool:
        original_shape = pipeline_utils.convert_str_to_tuple(metadata['shape'])
        print(f"This is the shape of the received image: {original_shape}")

        if self.qoaClient:
            self.qoaClient.observeMetric("image_width", original_shape[0], 1)
            self.qoaClient.observeMetric("image_height", original_shape[1], 1)
        
        model_metadata = self.MLAgent.get_model_metadata()
        for key in list(model_metadata.keys()):
            if self.qoaClient:
                self.qoaClient.observeInferenceMetric(key, model_metadata[key])
        if original_shape == self.MLAgent.input_shape:
            return True
        return False
    
    def _get_image_meta_data(self, request) -> Optional[Dict]:
        try:
            metadata_json = request.form.get('metadata')
            if metadata_json is None:
                return None  
            metadata = json.loads(metadata_json)
            return metadata
        except json.JSONDecodeError:
            return None  
    


# def load_minio_storage(storage_info):
#     minio_connector = MinioConnector(storage_info= storage_info)
#     return minio_connector

