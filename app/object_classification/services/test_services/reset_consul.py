import sys, os, argparse
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

import lib.roheUtils as roheUtils

from core.serviceRegistry.consul import ConsulClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'resetConsult.yaml')
    parser.add_argument('--id', type= str, help='specify service endpoint', 
                        default= '')
    
    args = parser.parse_args()
    config_file = args.conf
    config = roheUtils.load_config(file_path= config_file)
    consul_client = ConsulClient(config= config['service_registry']['consul_config'])
    for service in config["service"]:
        instance_list = consul_client.getAllServiceInstances(service)
        for instance in instance_list:
            result = consul_client.serviceDeregister(instance["ID"])
            if result:
                print("Service {}, instance {} deregister success".format(service, instance["ID"]))