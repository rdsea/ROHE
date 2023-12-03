import sys, os
import argparse


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


from app.object_classification.services.processing.processingService import ProcessingService
import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--port', type= int, help='default port', default=7000)
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'processing_config.yaml')
    parser.add_argument('--endpoint', type= str, help='specify service endpoint', 
                        default= '/processing_service_controller')
    
    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)
    endpoint = args.endpoint
    config_file = args.conf


    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['processing_config']['max_thread'] = int(config['processing_config']['max_thread'])
    config['processing_config']['min_waiting_period'] = int(config['processing_config']['min_waiting_period'])
    config['processing_config']['max_waiting_period'] = int(config['processing_config']['max_waiting_period'])

    # emulate the service registry
    config['inference_server'] = {}
    # config['inference_server']['urls'] = ("http://localhost:9000/inference_service","http://localhost:30000/inference_service")
    config['inference_server']['urls'] = ("http://localhost:9000/inference_service", "http://localhost:9900/inference_service")




    processing_service = ProcessingService(config= config,
                                           port= port, endpoint= endpoint)
    processing_service.run()


