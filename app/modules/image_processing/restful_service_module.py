
from flask import request
from lib.modules.restService.roheService import RoheRestObject
from .restful_service_controller import ServiceController, ControllerMangagement, BlankServiceController

import json

class RestfulServiceModule(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf: dict = configuration

        self.controller_state_manager: ControllerMangagement = self.conf.get('controller_manager')
        self.get_service_controller()
        self.service_controller: ServiceController = self.controller_state_manager.service_controller

        print(f"This is service controller: {self.service_controller}")

    def get_service_controller(self) -> ServiceController:
        if not self.controller_state_manager.service_controller:
            print("Never have service controller before")
            new_controller = self.conf.get('service_controller', None)
            if not new_controller:
                new_controller = BlankServiceController(config= None)
            self.controller_state_manager.update_controller(new_controller= new_controller)
        else:
            print("Already initilized service controller")
            

    def post(self):
        """
        Handles POST requests for rest service.

        """
        command = request.form.get('command')
        if command == "change_controller":
            print("About to change service controller")
            return self.change_service_controller(request)
        else:
            return self.service_controller.post_command_handler(request)

    def change_service_controller(self, request: request):
        # temporarily implement as this
        # since changing service controller is complicated
        service_controller = BlankServiceController(config= None)
        self.controller_state_manager.update_controller(service_controller)
        try:
            response = f"sucessfully update the controller"
            return json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print("Exception:", e)
            return json.dumps({"error": "An error occurred while updating the controller"}), 500, {'Content-Type': 'application/json'}

    def get(self):
        """
        Handles GET requests for rest service.

        """
        response = self.service_controller.get_command_handler(request)
        return response

    def put(self):
        """
        Handles PUT requests for rest service.

        """
        return self.service_controller.put_command_handler(request)

    def delete(self):
        """
        Handles DELETE requests for rest service.

        """
        return self.service_controller.delete_command_handler(request)
