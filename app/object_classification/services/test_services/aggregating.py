import sys, os
import argparse


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


from app.object_classification.services.aggregating.aggregatingService import AggregatingService
import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Aggregating Service")
    parser.add_argument('--port', type= int, help='default port', default=13000)
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'aggregating_service.yaml')
    parser.add_argument('--endpoint', type= str, help='specify service endpoint', 
                        default= '/aggregating_service_controller')
    
    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)
    endpoint = args.endpoint
    config_file = args.conf


    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)


    aggregating_service = AggregatingService(config= config,
                                           port= port, endpoint= endpoint)
    aggregating_service.run()


