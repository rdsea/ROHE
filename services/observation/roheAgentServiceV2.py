
import qoa4ml.utils as utils
import sys
main_path = config_file = utils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.observation.metricCollector.roheAgentV2 import Rohe_ObService
import argparse


from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/observation/observationConfig.json")
    parser.add_argument('--port', help='default port', default=5001)
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    port = int(args.port)
    if not config_file:
        config_file = utils.get_parent_dir(__file__,2)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)

    api.add_resource(Rohe_ObService, '/registration',resource_class_kwargs=configuration)
    app.run(debug=True, port=port)