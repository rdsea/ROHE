
import argparse
import os, sys
import qoa4ml.qoaUtils as qoa_utils
import redis


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 2
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)

print(main_path)

from app.modules.restful_service_module import RestfulServiceModule
from lib.modules.restService.roheService import RoheRestService


class RestfulService():
    def __init__(self, service_controller_resource: dict, 
                 service_endpoint: str, port: int):
        self.service = RoheRestService(service_controller_resource)
        self.service.add_resource(RestfulServiceModule, service_endpoint)
        self.run(port= int(port))

    def run(self, port):
        self.service.run(port= port)


def setup_redis(redis_config):
    return redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])


if __name__ == '__main__': 

    from app.modules.restful_service_controller import ControllerMangagement
    from app.modules.task_coordinator_serivce_controller import TaskCoordinatorServiceController


    import lib.roheUtils as roheUtils

    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "./task_coordinator.yaml")
    parser.add_argument('--service_endpoint', type= str, help='service endpoint', 
            default= "/task_coordinator")
    

    args = parser.parse_args()
    config_file = args.conf


    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)
        
    print(f"\n\nThis is config file: {config}\n\n")


    # load dependencies
    redis = setup_redis(redis_config= config['redis_server'])
    config['redis'] = redis
    
    task_coordinator_service_controller = TaskCoordinatorServiceController(config= config)
    
    controller_manager = ControllerMangagement()
    service_controller_resource = {
        'service_controller': task_coordinator_service_controller,
        # 'service_controller': None,
        'controller_manager': controller_manager,
    }


    service = RestfulService(service_controller_resource= service_controller_resource,
                             service_endpoint= args.service_endpoint,
                             port= args.port)
    