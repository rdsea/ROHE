import redis
from flask import request, jsonify
import argparse
import json

import sys, os


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


from lib import RoheRestObject, RoheRestService
import examples.applications.NII.utilities.utils as utils

class TaskCoordinator(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        log_lev = self.conf.get('log_lev', 2)
        self.set_logger_level(logging_level= log_lev)
        self.redis = self._setup_redis(self.conf['redis_server'])


    def _setup_redis(self, redis_config):
        redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])

    def post(self):
        """
        Handles POST requests to coordinate tasks between the ingestion and processing instances.

        Commands:
        1. add: Called by the ingestion instance to add an image to the queue for processing.
            Adds the image to the unprocessed_images list in Redis.

        2. complete: Called by the processing instance to indicate that an image has been fully processed.
            Removes the image metadata from the processing_images list and adds it to the processed_images list in Redis.

        :return: JSON response indicating the status of the command or an error message.
        """
        command = request.form.get('command')
        if command == 'add':
            return self._add_image()
        elif command == 'complete':
            return self._complete_processing()
        else:
            return jsonify({"error": "Invalid command"}), 400

    def get(self):
        """
        Handles GET requests from the processing instances to claim an image for processing.

        Functionality:
        - Moves an image metadata from the unprocessed_images list to the processing_images list in Redis.
        - Claims the image for a specific processing instance.

        :return: JSON response containing the claimed image or a status indicating no unprocessed images.
        """
        return self._claim_image()


    def _claim_image(self):
        serialized_image_info = self.redis.rpoplpush("unprocessed_images", "processing_images")
        if serialized_image_info:
            image_info = utils.deserialize(serialized_image_info)
            return json.dumps({"image_info": image_info}), 200, {'Content-Type': 'application/json'}
        else:
            return json.dumps({"status": "no unprocessed images"}), 404, {'Content-Type': 'application/json'}

    def _add_image(self):
        image_info = {
            'timestamp': request.form.get('timestamp'),
            'device_id': request.form.get('device_id'),
            'image_url': request.form.get('image_url')
        }
        if all(image_info.values()):
            serialized_image_info = utils.serialize(image_info)
            self.redis.lpush("unprocessed_images", serialized_image_info)
            return json.dumps({"status": "success"}), 200, {'Content-Type': 'application/json'}
        else:
            return json.dumps({"error": "Some required fields are missing"}), 400, {'Content-Type': 'application/json'}

    def _complete_processing(self):
        image_id = request.form.get('image_id')
        if image_id:
            self.redis.lrem("processing_images", 0, image_id)
            self.redis.lpush("processed_images", image_id)
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": "Image ID is missing"}), 400

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Task Coordinator Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', 
    default= "examples/applications/NII/kube_deployment/dataProcessingService/configurations/task_coordinator.json")
    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    port = int(args.port)
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    


    taskCoordinatorService = RoheRestService(config)
    taskCoordinatorService.add_resource(TaskCoordinator, '/task_coordinator')
    taskCoordinatorService.run(port=port)
