

from abc import ABC, abstractmethod


class ServiceController(ABC):
    def __init__(self, config):
        self.conf = config

    @abstractmethod
    def get_command_handler(self, request):
        pass

    @abstractmethod
    def post_command_handler(self, request):
        pass

    @abstractmethod
    def put_command_handler(self, request):
        pass

    @abstractmethod
    def delete_command_handler(self, request):
        pass

import json
class BlankServiceController(ServiceController):
    def __init__(self, config):
        self.conf = config

    def get_command_handler(self, request):
        try:
            response = f"This is a blank rest service. Please request to change to your desire service"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}


    def post_command_handler(self, request):
        try:
            response = f"This is a blank rest service. Please request to change to your desire service"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def put_command_handler(self, request):
        try:
            response = f"This is a blank rest service. Please request to change to your desire service"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}

    def delete_command_handler(self, request):
        try:
            response = f"This is a blank rest service. Please request to change to your desire service"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred"}), 500, {'Content-Type': 'application/json'}


class ControllerMangagement():
    def __init__(self):
        self.service_controller: ServiceController = None
    def update_controller(self, new_controller: ServiceController):
        self.service_controller = new_controller