from flask import Flask, request, jsonify
import logging
import sys
import os
import argparse
import yaml

parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)
logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)
from rohe.orchestration.multimodal_abstration import InferenceQuery
from rohe.orchestration.multimodal_orchestration import AdaptiveOrchestrator

DEFAULT_CONFIG_PATH = 'config.yaml'

app = Flask(__name__)  

control_plane_config = yaml.safe_load(open(DEFAULT_CONFIG_PATH, 'r'))

orchestrator_config_path = control_plane_config.get('orchestrator_config_path', '../config/orchestrator.yaml')

orchestrator = AdaptiveOrchestrator(config_path=orchestrator_config_path)


@app.route('/inference_request', methods=['POST'])
def inference_request():
    global debs_adaptive_orchestration
    request_data = request.get_json()
    query = InferenceQuery.model_validate(request_data)
    orchestration_result = orchestrator.orchestrate(query)
    
    return jsonify({'Response': orchestration_result}), 200

if __name__ == "__main__":
    config = yaml.safe_load(open(DEFAULT_CONFIG_PATH, 'r'))
    host = config.get('host', '0.0.0.0')
    port = config.get('port', 5123)
    app.run(host=host, port=port)