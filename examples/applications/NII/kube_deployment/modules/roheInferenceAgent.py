
from abc import ABC, abstractmethod
from flask import request, jsonify
from modules.roheObject import RoheObject
from flask_restful import Resource


class RoheInferenceAgent(RoheObject, Resource, ABC):
    def __init__(self, configuration, log_lev=2):
        super().__init__(logging_level=log_lev)

        self.conf = configuration

        #Init model configuration (architecture, weight file)
        model_conf = self.conf["model"]
        print(f"this is the model configuration: {model_conf}")

        self.model, self.input_shape = self.load_model(model_conf)

        self.post_command_handlers = {
            'predict': self.handle_predict_req,
            'modify_weights': self.handle_modify_weights_req,
            'modify_structure': self.handle_modify_structure_req,
        }

    def get(self):
        response = self.handle_get_request(request)
        return jsonify({'response': response}), 200
        
    # structure of client request
    # sample
    # payload = {'command': 'load_weight'}
    # files = {'weights': open('model_weights.h5', 'rb')}
    # requests.post('http://server-address/api-name', data=payload, files=files)
    def post(self):
        command = request.form.get('command')
        handler = self.post_command_handlers.get(command)

        if handler:
            response = handler(request)
            return jsonify({'response': response}), 200
        else:
            return jsonify({"response": "Command not found"}), 404


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
    
