import redis
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

up_level = 1
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)


from lib.services.restService import RoheRestService
from examples.applications.NII.kube_deployment.dataProcessingService.services.taskCoordinatorService import TaskCoordinator

def setup_redis(redis_config):
    return redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Task Coordinator Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "task_coordinator.json")
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

    # initialize dependecy before passing to the restful server
    redis = setup_redis(redis_config= config['redis_server'])

    config['redis'] = redis

    taskCoordinatorService = RoheRestService(config)
    taskCoordinatorService.add_resource(TaskCoordinator, '/task_coordinator')
    taskCoordinatorService.run(port=port)
