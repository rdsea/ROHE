import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils
import argparse
from flask import Flask
from flask_restful import Api

from core.orchestration.restAgent import RoheOrchestrationAgent, RoheOrchestrationService

app = Flask(__name__)
api = Api(app)
rohe_agent = None

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Orchestration Service")
    parser.add_argument('--port', help='server port', default=5002)
    parser.add_argument('--conf', help='configuration file', default=None)
    #parser.add_argument('--path', help='default config path', default="/configurations/orchestration/orchestrationConfigLocal.json")
    args = parser.parse_args()
    config_file = args.conf
    #config_path = args.path
    port = args.port
    if not config_file:
        print(f'Cannot handle config file={config_file}')
        sys.exit(1)
    #    config_file = qoaUtils.get_parent_dir(__file__,2)+config_path
    #    print(config_file)
    
    configuration = rohe_utils.load_config(config_file)
    rohe_agent = RoheOrchestrationAgent(configuration,False)
    configuration["agent"] = rohe_agent
    api.add_resource(RoheOrchestrationService, '/management',resource_class_kwargs=configuration)
    app.run(debug=True, port=port)