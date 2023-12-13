
import redis
import argparse
import sys, os
import signal


from dotenv import load_dotenv
load_dotenv()

ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)


import lib.roheUtils as roheUtils
from lib.rohe.restService import RoheRestService

from app.object_classification.services.image_info.imageInfoService import ImageInfoService

from lib.serviceRegistry.consul import ConsulClient
import app.object_classification.modules.utils as pipeline_utils
from qoa4ml.QoaClient import QoaClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Task Coordinator Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', default= 'image_info_config.yaml')
    parser.add_argument('--run', type= str, help='specify run ID', 
                        default= 'profiling1')


    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    port = int(args.port)

    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['external_services']['redis_server']['db'] = int(config['external_services']['redis_server']['db'])

    print(f"This is the config: {config}")

    
    # qoa
    if config.get('qoa_config'):
        config['qoa_config']['client']['runID'] = args.run
        print(f"\nAbout to load qoa client: {config['qoa_config']}")
        qoa_client = QoaClient(config['qoa_config'])
        qoa_client.process_monitor_start(5)
        config['qoaClient'] = qoa_client

   # consul for service register
    # register service
    local_ip = pipeline_utils.get_local_ip()
    consul_client = ConsulClient(config= config['external_services']['service_registry']['consul_config'])
    service_id = consul_client.serviceRegister(name= 'image_info', address= local_ip, tag=["nii_case"], port= port)

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C! Gracefully shutting down.')
        consul_client.serviceDeregister(id= service_id)
        sys.exit(0)

    # Register the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    # initialize dependecy before passing to the restful server
    # redis = setup_redis(redis_config= config['redis_server'])
    redis_config = config['external_services']['redis_server']
    redis = redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])
    config['redis'] = redis

    taskCoordinatorService = RoheRestService(config)
    taskCoordinatorService.add_resource(ImageInfoService, '/image_info_service')
    taskCoordinatorService.run(port=port)
