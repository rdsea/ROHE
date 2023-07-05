import qoa4ml.utils as utils
import argparse
import sys
main_path = config_file = utils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from modules.orchestration.roheOrchestrationAgent import Rohe_Orchestration_Agent, Rohe_Orchestration_Service


from flask import Flask
from flask_restful import Api

app = Flask(__name__)
api = Api(app)

rohe_agent = None



if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Orchestration Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/orchestration/orchestrationConfig.json")
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    if not config_file:
        config_file = utils.get_parent_dir(__file__,1)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)
    rohe_agent = Rohe_Orchestration_Agent(configuration,False)
    configuration["agent"] = rohe_agent

    api.add_resource(Rohe_Orchestration_Service, '/management',resource_class_kwargs=configuration)
    app.run(debug=True, port=5002)