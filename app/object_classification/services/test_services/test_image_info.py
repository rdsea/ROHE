
import redis
import argparse
import sys, os


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


import lib.roheUtils as roheUtils
from app.object_classification.lib.roheService import RoheRestService
from app.object_classification.services.imageInfoService import ImageInfoService



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Task Coordinator Service")
    parser.add_argument('--port', type= int, help='default port', default=5000)
    parser.add_argument('--conf', type= str, help='configuration file', default= 'image_info_service_config.yaml')


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
    # redis = setup_redis(redis_config= config['redis_server'])
    redis_config = config['redis_server']
    redis = redis.Redis(host= redis_config['host'], port=redis_config['port'], db= redis_config['db'])
    config['redis'] = redis

    taskCoordinatorService = RoheRestService(config)
    taskCoordinatorService.add_resource(ImageInfoService, '/image_info_server')
    taskCoordinatorService.run(port=port)
