import traceback
import sys
import argparse
#main_path = config_file = qoaUtils.get_parent_dir(__file__,2)
#sys.path.append(main_path)
# from lib.services.observation.roheAgenStreaming import RoheObservationAgent
from lib.modules.restService.roheService import RoheRestService
import lib.roheUtils as rohe_utils
from lib.modules.observation.services.roheObservation import RoheObservation, RoheRegistration



#DEFAULT_CONFIG_PATH="/config/observationConfig.yaml"

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--port', help='default port', default=5010)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    #config_path = args.path
    port = int(args.port)

    # load configuration file
    if not config_file:
        #config_file = main_path+DEFAULT_CONFIG_PATH
        #print(config_file)
        print(f'Error with configuration file config_file={config_file}')
        sys.exit(1)
    try:
        configuration = rohe_utils.load_config(config_file)
        observationService = RoheRestService(configuration)
        observationService.add_resource(RoheObservation, '/agent')
        observationService.add_resource(RoheRegistration, '/registration')
        observationService.run(port=port)
    except:
        traceback.print_exc()