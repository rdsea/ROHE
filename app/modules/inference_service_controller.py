

import os
import json
import numpy as np
from flask import request
from typing import Dict, Optional

from app.modules.image_processing.classificationObject import ClassificationObjectV1
from app.modules.service_connectors.broker_connectors.quixStreamProducer import KafkaStreamProducer
from app.modules.service_connectors.storage_connectors.minioStorageConnector import MinioConnector
from app.modules.service_connectors.storage_connectors.mongoDBConnector import MongoDBConnector

from .restful_service_module import ServiceController


class EnsembleState():
    def __init__(self, mode: bool):
        self.mode = mode
        
    def change_mode(self, mode: bool):
        self.mode = mode

    def get_mode(self) -> bool:
        return self.mode
    
class InferenceServiceController(ServiceController):
    def __init__(self, config):
        super().__init__(config)
        self.qoaClient = self.conf.get('qoaClient')

        self.MLAgent: ClassificationObjectV1 = self.conf.get('MLAgent')
        self.ensemble_controller: EnsembleState = self.conf['ensemble_controller']
        self.minio_connector: MinioConnector = self.conf['minio_connector']
        self.kafka_producer: KafkaStreamProducer = self.conf['kafka_producer'] 
        self.mongo_connector: MongoDBConnector = self.conf['mongo_connector'] 
        

        # set model lock
        self.model_lock = self.conf['lock']
        self.pipeline_id = self.conf.get('pipeline_id') or "pipeline_sample"


        self.post_command_handlers = {
            'predict': self._handle_predict_req,
            'load_new_weights': self._handle_load_new_weights_req,
            'load_new_model': self._handle_load_new_model_req,
            'change_ensemble_mode': self._handle_change_ensemble_mode,
        }

    def get_command_handler(self, request):
        try:
            response = self._handle_get_request(request)
            # print(f"This is response: {response}")
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def _handle_get_request(self, request):
        return f"Hello from Rohe Object Classification Server. This is the input shape: {self.MLAgent.input_shape}"


    def post_command_handler(self, request):
        try:
            command = request.form.get('command')
            handler = self.post_command_handlers.get(command)

            if handler:
                response = handler(request)
                print(f"\n\nThis is the response: {response}")

                if self.qoaClient:
                    self.qoaClient.timer()
                    
                result = json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
                print(f"This is the result: {result}")
            else:
                result = json.dumps({"response": "Command not found"}), 404, {'Content-Type': 'application/json'}
            
        except Exception as e:
            print("Exception:", e)
            result = json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}
        
        if command == "predict":
            try:
                if self.qoaClient:
                    self.qoaClient.observeInferenceMetric("confidence", float(response['confidence_level']))
            except Exception as e:
                print(e)


        if self.qoaClient:
            report = self.qoaClient.report(submit=True)
#             print(report)


        return result
    
    def put_command_handler(self, request):
        try:
            response = self._handle_put_request(request)
            # print(f"This is response: {response}")
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def _handle_put_request(self, request):
        return f"Does not support this operation yet"

    
    def delete_command_handler(self, request):
        try:
            response = self._handle_delete_request(request)
            # print(f"This is response: {response}")
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def _handle_delete_request(self, request):
        return f"Does not support this operation yet"


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
        # if self.ensemble == True:
        mode = self.ensemble_controller.get_mode() == True
        # print(f"This is the mode: {mode}")
        print(f"\n\n The mode when forwarding result: {mode}, the mode of ensemble state: {self.ensemble_controller.get_mode()}")
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

        if self.ensemble_controller.get_mode() == True:
            print("process message for kafka ensemble")
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

    # # Send POST request
    # response = requests.post('http://server-address/api-name', json=payload)
    def _handle_load_new_model_req(self, request: request):
        local_file = request.form.get('local_file')
        if local_file:
            return self._handle_load_new_local_model_req(request)


    def _handle_change_ensemble_mode(self, request: request):
        try:
            ensemble_mode = request.form.get('ensemble_mode')
            # ensemble_mode = request.form.get('ensemble_mode')
            ensemble_mode = ensemble_mode.lower() == 'true'

            # ensemble_mode= bool(request.form.get('ensemble_mode'))
            print(f"\n\n\n\nThis is the request ensemble mode: {ensemble_mode}")     
            message = f"Successfully change the ensemble mode from {self.ensemble_controller.get_mode()} to {ensemble_mode}"
            with self.model_lock:
                print(f"Mode before changing: {self.ensemble_controller.get_mode()}")
                self.ensemble_controller.change_mode(ensemble_mode)
                # print(f"The current ensemble mode after making request: {self.ensemble_controller.get_mode()}\n\n\n")
                print(f"Mode after changing: {self.ensemble_controller.get_mode()}")

            return message
                
        except Exception as e:
            return f"Local model case. Failed to update new weights or architecture: {str(e)}"


    def _handle_load_new_local_model_req(self, request: request):
        try:
            chosen_model_id: str = request.form.get('model_id')
            files = self.MLAgent.get_model_files(chosen_model_id)
            
            new_model = self.MLAgent.load_model_from_config(**files)

            with self.model_lock:
                self.MLAgent.change_model(new_model)
                self.MLAgent.set_model_id(chosen_model_id)
                print(f"\n\n\nThis is the current model id: {self.MLAgent.get_model_id()}")
            
            return "Local file case. Sucessfully change the model"
                
        except Exception as e:
            return f"Local model case. Failed to update new weights or architecture: {str(e)}"


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
