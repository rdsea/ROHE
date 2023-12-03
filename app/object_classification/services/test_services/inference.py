import sys, os
import argparse


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


# from app.object_classification.services.processing.processingService import ProcessingService
from app.object_classification.services.inference.inferenceService import InferenceService
import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--port', type= int, help='default port', default=9000)
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'inference_service.yaml')
    parser.add_argument('--executor_endpoint', type= str, help='specify service endpoint', 
                        default= '/inference_service')
    parser.add_argument('--controller_endpoint', type= str, help='specify service endpoint', 
                        default= '/inference_service_controller')

    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)
    executor_endpoint = args.executor_endpoint
    controller_endpoint = args.controller_endpoint

    config_file = args.conf


    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)



    inference_service = InferenceService(config= config, port= port, 
                                         executor_endpoint= executor_endpoint,
                                         controller_endpoint= controller_endpoint)
    inference_service.run()


