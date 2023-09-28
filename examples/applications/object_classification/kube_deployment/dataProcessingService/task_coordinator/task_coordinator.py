
import redis
import argparse
import sys, os

import qoa4ml.qoaUtils as qoa_utils


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 6

main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)


from lib.services.restService import RoheRestService
from lib.services.object_classification.taskCoordinatorService import TaskCoordinator
import lib.roheUtils as roheUtils

def setup_redis(redis_config):
    return redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Task Coordinator Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', default= 'task_coordinator.yaml')


    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    port = int(args.port)

    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['redis_server']['db'] = int(config['redis_server']['db'])

    print(f"This is the config: {config}")

    # initialize dependecy before passing to the restful server
    redis = setup_redis(redis_config= config['redis_server'])

    config['redis'] = redis

    taskCoordinatorService = RoheRestService(config)
    taskCoordinatorService.add_resource(TaskCoordinator, '/task_coordinator')
    taskCoordinatorService.run(port=port)
