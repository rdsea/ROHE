import os, sys
import json
import numpy as np
import argparse
from dotenv import load_dotenv
load_dotenv()
from flask import request
import threading

from typing import Dict, Optional


# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 7
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)

from examples.applications.NII.kube_deployment.inferenceService.modules import ClassificationObject
from examples.applications.NII.utilities import MinioConnector
from examples.applications.NII.utilities.utils import get_image_dim_from_str
from lib import RoheRestObject, RoheRestService


class ClassificationRestService(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration

        log_lev = self.conf.get('log_lev', 2)
        self.set_logger_level(logging_level= log_lev)

        # set up minio storage connector
        self.minio_connector = self._load_minio_storage(storage_info= self.conf.get('minio_config', {})) 

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

        self.MLAgent = ClassificationObject(files= configuration['model']['files'],
                                            input_shape= configuration['model']['input_shape'],
                                            model_from_config= True)
        self.model_lock = threading.Lock()

        self.post_command_handlers = {
            'predict': self._handle_predict_req,
            'load_new_weights': self._handle_load_new_weights_req,
            'load_new_model': self._handle_load_new_model_req,
        }

    
    def _load_minio_storage(self, storage_info):
        minio_connector = MinioConnector(storage_info= storage_info)
        return minio_connector

    
    def post(self):
        """
        Handles POST requests for the inference service.

        Command Descriptions:
        - load_new_weights: Loads a new set of weights for the model.
        - load_new_model: Loads a new machine learning model for inference.
        - predict: download the image and returns a prediction.
        """

        try:
            command = request.form.get('command')
            handler = self.post_command_handlers.get(command)

            if handler:
                response = handler(request)
                return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
            else:
                return json.dumps({"response": "Command not found"}), 404, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def get(self):
        try:
            response = self.handle_get_request(request)
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}


    def handle_get_request(self, request):
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
                        return result
                except:
                    return "something wrong with the model"
            else:
                return "something wrong with the retrieving image process"
        else:
            return f"Image shape is not matched with the input shape of the model {self.MLAgent.input_shape} "
            
    def _check_dim(self, metadata) -> bool:
        original_shape = get_image_dim_from_str(metadata['shape'])
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
        else:
            return self._handle_load_new_remote_weights_req(request)

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

    def _handle_load_new_remote_weights_req(self, request: request):
        remote_file_path = request.form.get('weights_url')
        local_file_path = './tmp_weights_file.h5'
        success = self.minio_connector.download(remote_file_path= remote_file_path,
                                                         local_file_path= local_file_path)
        if success:
            try:
                with self.model_lock:
                    self.MLAgent.load_weights(local_file_path)
            # after loading the weight, delete the local file
            except:
                os.remove(local_file_path)
                return "fail to update new weights (layers doesn't match)"

            os.remove(local_file_path) 
            return "successfully update new weights"
        else:
            return "cannot download the files"

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
        else:
            return self._handle_load_new_remote_model_req(request)

    def _handle_load_new_local_model_req(self, request: request):
        try:
            files = {
                "weights_file": request.form.get('weights_url'),
                "architecture_file": request.form.get('architecture_url')
            }
            
            new_model = self.MLAgent.load_model(files= files)

            with self.model_lock:
                self.MLAgent.change_model(new_model)
            
            return "Local file case. Sucessfully change the model"
                
        except Exception as e:
            return f"Local model case. Failed to update new weights or architecture: {str(e)}"


    def _handle_load_new_remote_model_req(self, request: request):
        # Download weights file
        weight_remote_file_path = request.form.get('weights_url')
        weight_local_file_path = './tmp_weights_file.h5'
        success = self.minio_connector.download(remote_file_path=weight_remote_file_path,
                                                    local_file_path=weight_local_file_path)
        if not success:
            return "cannot download the weights file"
        # Download architecture file
        architecture_remote_file_path = request.form.get('architecture_url')
        architecture_local_file_path = './tmp_architecture_file.json'
        success = self.minio_connector.download(remote_file_path=architecture_remote_file_path,
                                                        local_file_path=architecture_local_file_path)
        if success:
            try:
                files = {
                    "architecture_file": architecture_local_file_path,
                    "weights_file": weight_local_file_path
                }
                new_model = self.MLAgent.load_model(files= files)
                with self.model_lock:
                    self.MLAgent.change_model(new_model)
                
                return "Remote case. Successfully change the model"

            except Exception as e:
                # Cleanup and return failure
                os.remove(weight_local_file_path)
                os.remove(architecture_local_file_path)
                return f"Failed to update new weights or architecture: {str(e)}"

            # Cleanup
            os.remove(weight_local_file_path)
            os.remove(architecture_local_file_path)
            # only update the current model if successfully load both the config and weight
            self.model = self.new_model
            return "Successfully updated new weights and architecture"

        else:
            return "cannot download the json file"

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



if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=9000)

    parser.add_argument('--conf', type= str, help='configuration file', 
    default= "examples/applications/NII/kube_deployment/inferenceService/configurations/inference_service.json")

    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")
    
    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)
