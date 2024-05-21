import sys, os
import argparse
import signal

from dotenv import load_dotenv
load_dotenv()

ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)


from app.object_classification.services.processing.processingService import ProcessingService
import lib.roheUtils as roheUtils
from qoa4ml.QoaClient import QoaClient
from core.serviceRegistry.consul import ConsulClient

import app.object_classification.modules.utils as pipeline_utils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--port', type= int, help='default port', default=7000)
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'processing_config.yaml')
    parser.add_argument('--endpoint', type= str, help='specify service endpoint', 
                        default= '/processing_service_controller')
    parser.add_argument('--run', type= str, help='specify run ID', 
                        default= 'profiling1')
    
    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)
    endpoint = args.endpoint
    config_file = args.conf


    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    # service registry
    local_ip = pipeline_utils.get_local_ip()
    consul_client = ConsulClient(config= config['external_services']['service_registry']['consul_config'])
    service_id = consul_client.serviceRegister(name= 'processing', address= local_ip, tag=["nii_case"], port= port)

    # query for image info service url
    image_info_tags = config['external_services']['service_registry']['service']['image_info']['tags']
    image_info_query_type = config['external_services']['service_registry']['service']['image_info']['type']
    # for now, assume that we just need one image info service 
    service_info = pipeline_utils.handle_service_query(consul_client= consul_client, 
                                                       service_name= 'image_info',
                                                       query_type= image_info_query_type,
                                                       tags= image_info_tags)[0]

    image_info_endpoint = 'image_info_service'
    image_info_endpoint = f"http://{service_info['Address']}:{service_info['Port']}/{image_info_endpoint}"
    config['image_info_service'] = {}
    config['image_info_service']['url'] = image_info_endpoint
    print(f"This is image info endpoint: {image_info_endpoint}")

    # inference services
    inference_tags = config['external_services']['service_registry']['service']['inference']['tags']
    inference_query_type = config['external_services']['service_registry']['service']['inference']['type']

    inference_service_info = pipeline_utils.handle_service_query(consul_client= consul_client, 
                                                       service_name= 'inference',
                                                       query_type= inference_query_type,
                                                       tags= inference_tags)
    inference_urls = []                                             
    inference_endpoint = 'inference_service'
    for service_info in inference_service_info:
        url = f"http://{service_info['Address']}:{service_info['Port']}/{inference_endpoint}"
        inference_urls.append(url)
    inference_urls = tuple(inference_urls)
    config['inference_server'] = {}
    config['inference_server']['urls'] = inference_urls
    print(f"This is inference urls: {config['inference_server']['urls']}")

    # qoa
    if config.get('qoa_config'):
        config['qoa_config']['client']['run_id'] = args.run
        print(f"\nAbout to load qoa client: {config['qoa_config']}")
        qoa_client = QoaClient(config['qoa_config'])
        qoa_client.process_monitor_start(5)
        config['qoaClient'] = qoa_client

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C! Gracefully shutting down.')
        consul_client.serviceDeregister(id= service_id)
        sys.exit(0)

    # Register the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)




    processing_service = ProcessingService(config= config,
                                           port= port, endpoint= endpoint)
    processing_service.run()


