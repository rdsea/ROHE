import os
import json
import numpy as np
from flask import request
from typing import Dict, Optional
import random


from lib.modules.object_classification.classificationObject import ClassificationObjectV1
from lib.service_connectors.minioStorageConnector import MinioConnector
from lib.service_connectors.mongoDBConnector import MongoDBConnector
from lib.service_connectors.quixStreamProducer import KafkaStreamProducer

from lib.services.restService import RoheRestObject

from qoa4ml.QoaClient import QoaClient


# class ClassificationRestService():
class ClassificationRestService(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        if 'qoaClient' in self.conf:
            print(f"There is qoa enable in the server")
            self.qoaClient: QoaClient = self.conf['qoaClient']
        else:
            self.qoaClient = None
        log_lev = self.conf.get('log_lev', 2)
        self.set_logger_level(logging_level= log_lev)

        self.ensemble = self.conf['ensemble'] or False
        self.pipeline_id = self.conf.get('pipeline_id') or "pipeline_sample"

        print(f"This is the ensemble mode: {self.ensemble}")
        #Init model configuration (architecture, weight file)
        ############################################################################################################################################
        # The REST AGENT should not manage ML model. We should separate REST and ML -> Use classificationObject in module to manage ML models
        # for example:
        # self.MLAgent = classificationObject()
        # later usage:
        # - get LOAD command from post: self.MLAgent.load(...)
        # - get INFERENCE command from post: self.MLAgent.inference(...)
        # - others: set/get weight, modify structure...
        ############################################################################################################################################

        # set minio storage connector
        self.minio_connector = self.conf['minio_connector']

        # set model handler module
        self.MLAgent: ClassificationObjectV1 = self.conf['MLAgent']

        # # forwarding to the next stage
        # # either to mongodb or kafka topic
        # # depend on the configuration
        # if self.ensemble:
        #     print("choose the ensemble mode")
        #     # set kafka streaming connector
        #     self.kafka_producer: KafkaStreamProducer = self.conf['kafka_producer'] 
        # else:
        #     print("mongo is chosen")
        #     # set mongodb connector
        #     self.mongo_connector: MongoDBConnector = self.conf['mongo_connector'] 

        # initialized both
        # to be flexible to switch mode 
        # between send to kafka topic
        # and send to mongodb 
        # set kafka streaming connector
        self.kafka_producer: KafkaStreamProducer = self.conf['kafka_producer'] 
        # set mongodb connector
        self.mongo_connector: MongoDBConnector = self.conf['mongo_connector'] 
        

        # set model lock
        self.model_lock = self.conf['lock']

        self.post_command_handlers = {
            'predict': self._handle_predict_req,
            'load_new_weights': self._handle_load_new_weights_req,
            'load_new_model': self._handle_load_new_model_req,
        }

    
    def post(self):
        """
        Handles POST requests for the inference service.

        Command Descriptions:
        - load_new_weights: Loads a new set of weights for the model.
        - load_new_model: Loads a new machine learning model for inference.
        - predict: download the image and returns a prediction.
        """
        if self.qoaClient:
            self.qoaClient.timer() 
        try:
             

            command = request.form.get('command')
            handler = self.post_command_handlers.get(command)

            if handler:
                response = handler(request)
                if self.qoaClient:
                    self.qoaClient.timer()
                result = json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
            else:
                result = json.dumps({"response": "Command not found"}), 404, {'Content-Type': 'application/json'}
            
        except Exception as e:
            print("Exception:", e)
            result = json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}
        
        if self.qoaClient:
            self.qoaClient.timer() 
        if command == "predict":
            try:
                if self.qoaClient:
                    self.qoaClient.observeInferenceMetric("confidence", float(response['confidence_level']))
            except Exception as e:
                print(e)

        if self.qoaClient:
            report = self.qoaClient.report(submit=True)

        return result

    def get(self):
        try:
            response = self._handle_get_request(request)
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}


    def _handle_get_request(self, request):
        return f"Hello from Rohe Object Classification Server. \nThis is the input shape: {self.MLAgent.input_shape}"


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
            image = self._retrieve_image(binary_encoded, dtype)
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
        if self.ensemble:
            print("About to send message to kafka topic")
            self.kafka_producer.produce_values(message= message)
        else:
            # print(f"This is the published data: {message}, and its type: {type(message)}")
            # Use the upload method to upload the data
            try:
                self.mongo_connector.upload([message])
                print('Data uploaded successfully.')
            except Exception as e:
                print(f'Failed to upload data. Error: {e}')

    def _generate_publish_message(self, request_info, prediction):
        print(f"\n\n\n This is the prediction: {prediction}")
        pred = prediction["prediction"]
        # print(f"\n\n\n\n\n\n This is the type of the prediction: {type(pred)}\n\n")

        message = {
            "request_id": request_info['request_id'],
            "prediction": pred,
            "pipeline_id": self.pipeline_id,
            "inference_model_id": self.MLAgent.get_model_id(),
        }
        if self.ensemble:
            message = self._proccess_message_for_ensemble(message= message)

        print(f"This is the message: {message}\n\n\n")
        return message
    
    def _proccess_message_for_ensemble(self, message):
        message['prediction'] = np.array(message['prediction'])
        return message
    
    def _check_dim(self, metadata) -> bool:
        original_shape = get_image_dim_from_str(metadata['shape'])
        print(f"This is the shape of the received image: {original_shape}")
        # print(f"This is the shape of the received image: {original_shape}")
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
    
    # payload = {
    #     'command': 'modify_weights',
    #     'local_file': True,
    #     'weights_url': 'weight-file-name.h5',
    # }
    # # Send POST request
    # response = requests.post('http://server-address/api-name', json=payload)
    def _handle_load_new_weights_req(self, request: request):
        local_file = request.form.get('local_file')
        if local_file:
            return self._handle_load_new_local_weights_req(request)
        # else:
        #     return self._handle_load_new_remote_weights_req(request)

    def _handle_load_new_local_weights_req(self, request: request):
        local_file_path = request.form.get('weights_url')
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
        local_file = request.form.get('local_file')
        if local_file:
            return self._handle_load_new_local_model_req(request)
        # else:
        #     return self._handle_load_new_remote_model_req(request)

    def _handle_load_new_local_model_req(self, request: request):
        try:
            print (request.form.get('weights_url'))
            files = {
                "weights_file": request.form.get('weights_url'),
                "architecture_file": request.form.get('architecture_url')
            }
            
            new_model = self.MLAgent.load_model_from_config(**files)

            with self.model_lock:
                self.MLAgent.change_model(new_model)
            
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

    def _retrieve_image(self, binary_encoded, dtype):
        try:
            image = np.frombuffer(binary_encoded.read(), dtype=dtype)
            image = image.reshape(self.MLAgent.input_shape)
        except:
            image = None
        return image


def load_minio_storage(storage_info):
    minio_connector = MinioConnector(storage_info= storage_info)
    return minio_connector


def get_image_dim_from_str(str_obj) -> tuple:
    return tuple(map(int, str_obj.split(',')))