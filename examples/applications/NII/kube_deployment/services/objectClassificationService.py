import os, sys
import json

import tensorflow as tf
import numpy as np

import argparse

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from flask_restful import Api

# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 6
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)

from examples.applications.NII.kube_deployment.modules import ObjectClassificationAgent
from examples.applications.NII.utilities import MinioConnector

app = Flask(__name__)
api = Api(app)
local_agent_list = {}


# class ObjectClassificationSerivce(RoheInferenceAgent):
#     def __init__(self, configuration, log_lev= 2):
#         super().__init__(configuration= configuration, log_lev= log_lev)

#         storage_info = configuration['minio_config']
#         self.minio_connector = self.load_minio_storage(storage_info= storage_info)
class ObjectClassificationSerivce(ObjectClassificationAgent):
    def __init__(self, **kwargs):
        configuration = kwargs.get('configuration', {})
        log_lev = kwargs.get('log_lev', 2)
        super().__init__(configuration=configuration, log_lev=log_lev)

    def load_model(self, conf):
        # assume that need both architecture file and weights file to load the model
        # because we don't have the code to create model architecture
        # architecture format: .json
        # weight format: .h5
        architecture_file = conf['architecture']
        weights_file = conf['weights']
        input_shape = conf['input_shape']
        input_shape = tuple(map(int, input_shape.split(',')))

        with open(architecture_file, 'r') as f:
            model_architecture = json.load(f)
            model=tf.keras.models.model_from_config(model_architecture)
            model.load_weights(weights_file)

        return model, input_shape
    
    def load_minio_storage(self, storage_info):
        minio_connector = MinioConnector(storage_info= storage_info)
        return minio_connector

    
    def handle_get_request(self, request):
        return "Hello from Rohe Object Classification Server"
    
    
    # # Convert the numpy array to bytes
    # image_bytes = image_np.tobytes()
    # # Metadata and command
    # metadata = {'shape': '32,32,3', 'dtype': str(image_np.dtype)}
    # payload = {'command': 'predict', 'metadata': json.dumps(metadata)}
    # files = {'image': ('image', image_bytes, 'application/octet-stream')}
    # requests.post('http://server-address/api-name', data=payload, files=files)
    def handle_predict_req(self, request: request):
        # Convert the binary data to a numpy array and decode the image
        image = self.retrieve_image(request)
        if image:
            image = image[np.newaxis, ...]  # Add a batch dimension
            try:
                prediction = self.model.predict(image)
                predicted_class_index = np.argmax(prediction)
                confidence_level = prediction[0, predicted_class_index]
                return {"class": predicted_class_index, "confidence_level": confidence_level}
            except:
                return "something wrong.."

    # payload = {
    #     'command': 'modify_weights',
    #     'minio_url': 'weight-file-name.h5',
    # }
    # # Send POST request
    # response = requests.post('http://server-address/api-name', json=payload)
    def handle_modify_weights_req(self, request: request):
        remote_file_path = request.form.get('minio_url')
        local_file_path = './tmp_weights_file.h5'
        success = self.minio_connector.download(remote_file_path= remote_file_path,
                                                         local_file_path= local_file_path)
        if success:
            try:
                self.model.load_weights(local_file_path)
            # after loading the weight, delete the local file
            except:
                os.remove(local_file_path)
                return "fail to update new weights (dim doesn't match)"

            os.remove(local_file_path) 
            return "successfully update new weights"
        else:
            return "cannot download the file"

    # payload = {
    #     'command': 'modify_weights',
    #     'minio_url': 'weight-file-name.h5',
    #     'architecture_url': 'architecture-file-name.json'
    # }
    # # Send POST request
    # response = requests.post('http://server-address/api-name', json=payload)
    def handle_modify_structure_req(self, request: request):
        # Download weights file
        weight_remote_file_path = request.form.get('minio_url')
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
                # Load architecture from JSON
                with open(architecture_local_file_path, 'r') as json_file:
                    json_config = json_file.read()
                self.new_model=tf.keras.models.model_from_config(json_config)

                # Load weights
                self.new_model.load_weights(weight_local_file_path)

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

    def retrieve_image(self):
        metadata_json = request.form.get('metadata')
        metadata = json.loads(metadata_json)
        original_shape = tuple(map(int, metadata['shape'].split(',')))
        # only process if the dim of image matches the input of the model
        if original_shape != self.input_shape:
            return []
        dtype = np.dtype(metadata['dtype'])

        image_file = request.files['image']
        image = np.frombuffer(image_file.read(), dtype=dtype)
        image = image.reshape(original_shape)
        return image


if __name__ == '__main__': 

    up_level = 6
    root_path = get_parent_dir(__file__, up_level)
    sys.path.append(root_path)
    print(root_path)

    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
                        default= "server_config.json")
    parser.add_argument('--port', type= int, help='default port', default=9000)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    port = int(args.port)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    config['configuration']['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    config['configuration']['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")
    
    # Run the Observation Service
    api.add_resource(ObjectClassificationSerivce, '/inference_service',resource_class_kwargs= config)
    
    app.run(debug=True, port=port,host="0.0.0.0")