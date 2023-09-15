
import qoa4ml.qoaUtils as qoaUtils
import argparse
import sys
main_path = config_file = qoaUtils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.observation.metricCollector.roheAgentV1 import Observability_Agent, Agent_Service


from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Mangement Service")
    parser.add_argument('--conf', help='configuration file', default="./conf.json")
    parser.add_argument('--port', help='default port', default=5000)
    args = parser.parse_args()
    config = qoaUtils.load_config(args.conf)
    port = int(args.port)
    agent = Observability_Agent(config)

    api.add_resource(Agent_Service, '/agent',resource_class_kwargs={"agent": agent})
    app.run(debug=True, port=port)