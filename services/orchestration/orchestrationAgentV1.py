import qoa4ml.qoaUtils as qoaUtils
import argparse
from flask import Flask
from flask_restful import Api
import matplotlib

import sys
main_path = config_file = qoaUtils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.orchestration.analysisProfiling.analysisAgent import Analysis_Agent, Analysis_Service

app = Flask(__name__)
api = Api(app)
matplotlib.use('Agg')


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Mangement Service")
    parser.add_argument('--conf', help='configuration file', default="./conf.json")
    parser.add_argument('--port', help='default port', default=5010)
    args = parser.parse_args()
    port = int(args.port)
    config = qoaUtils.load_config(args.conf)
    agent = Analysis_Agent(config)

    api.add_resource(Analysis_Service, '/agent',resource_class_kwargs={"agent": agent})
    app.run(debug=True, port=port)