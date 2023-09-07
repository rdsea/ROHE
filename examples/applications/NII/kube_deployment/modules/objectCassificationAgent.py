
from abc import ABC, abstractmethod
from flask import request, jsonify
from modules.roheObject import RoheObject
from flask_restful import Resource

import json

class ObjectClassificationAgent(RoheObject, Resource, ABC):
    def __init__(self, configuration, log_lev=2):
        super().__init__(logging_level=log_lev)

        self.conf = configuration

        #Init model configuration (architecture, weight file)
        model_conf = self.conf["model"]

        self.model, self.input_shape = self.load_model(model_conf)

        self.post_command_handlers = {
            'predict': self.handle_predict_req,
            'modify_weights': self.handle_modify_weights_req,
            'modify_structure': self.handle_modify_structure_req,
        }

    def get(self):
        try:
            response = self.handle_get_request(request)
            print("Response:", response)  # Debugging line to see what exactly is the response
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)  # Debugging line to see what exception was thrown
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    # structure of client request
    # sample
    # payload = {'command': 'load_weight'}
    # files = {'weights': open('model_weights.h5', 'rb')}
    # requests.post('http://server-address/api-name', data=payload, files=files)

    def post(self):
        try:
            command = request.form.get('command')
            handler = self.post_command_handlers.get(command)

            if handler:
                response = handler(request)
                print("Response:", response)  # Debugging line to see what exactly is the response
                return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
            else:
                return json.dumps({"response": "Command not found"}), 404, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)  # Debugging line to see what exception was thrown
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}


    @abstractmethod
    def load_model(self, conf):
        '''
        return both the model
        and the config input shape
        '''
        pass


    @abstractmethod
    def handle_get_request(self, request):
        pass

    @abstractmethod
    def handle_predict_req(self, request):
        pass

    @abstractmethod
    def handle_modify_structure_req(self, request):
        pass

    @abstractmethod
    def handle_modify_weights_req(self, request):
        pass
    
