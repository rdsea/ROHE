import torch
import argparse
import json
import logging
import time
import traceback
from flask import Flask, request, jsonify
import joblib
import duckdb
import socket
import uuid
import yaml
import os
import numpy as np
import sys
import requests
logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)

app = Flask(__name__)

TOP_K = 10

def get_local_ip():
    try:
        # get IP address by asking dns server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("eth0", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except socket.gaierror:
        try:
            # Method 2: Connect to a remote address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # Method 3: Use localhost as fallback
            logging.warning("Failed to get local IP address, using localhost")
            return "0.0.0.0"

# DuckDB for testing
db_path = "../../database/"
db_dir = os.path.dirname(db_path)
db_file = os.path.join(db_dir, "file.duckdb")   
conn = duckdb.connect(db_file)


INSTANCE_TABLE = "inference_service_instance"
SERVICE_TABLE = "inference_service"


# get the hostname of the current machine
hostname = socket.gethostname()
logging.info(f"Hostname: {hostname}")

# get ip address of current machine
ip_address = get_local_ip()
logging.info(f"IP Address: {ip_address}")



# generate a unique instance ID
instance_id = str(uuid.uuid4())

# get ports of all instances having the same ip address and get the highest port
ports = conn.execute(f"""
SELECT port FROM {INSTANCE_TABLE} WHERE ip_address = '{ip_address}';
""").fetchall()

if ports:
    port = max([p[0] for p in ports]) + 1
else:
    port = 6666  # default port if not found

logging.info(f"Using port: {ports}")
logging.info(f"Selected port: {port}")

config = yaml.safe_load(open("config.yaml"))

model_name = config.get("model_name", "mini_rocket")
device = config.get("device", "acc_phone_clip")
test_run = config.get("test_run", False)
version = config.get("version", 0)
host = ip_address
device_id = hostname
data_hub = config.get("data_hub", "http://localhost:5550")

# Register the inference service instance in the database
conn.execute(f"""
INSERT INTO {INSTANCE_TABLE} (instance_id, model_id, model_version, device_id, ip_address, port, data)
VALUES ('{instance_id}', '{model_name}', '{version}', '{device_id}', '{ip_address}', {port}, 'None');
""")
conn.commit()
conn.close()

folder_path = f"./model/{model_name}/{device}/v{version}/"
logging.info(f"Loading model from: {folder_path}")
minirocket = joblib.load(f'{folder_path}minirocket.pkl')
classifier = joblib.load(f'{folder_path}classifier.pkl')
label_mapping = joblib.load(f'{folder_path}label_mapping.pkl')

@app.route('/inference', methods=['POST'])
def inference():
    start_time = time.time()
    global minirocket, classifier, label_mapping, data_hub, instance_id, model_name, version, device_id
    try:
        # Read byte data from the request
        # get inf_id from request
        request_data = request.get_json()
        if not request_data or 'inf_id' not in request_data:
            return jsonify({"error": "inf_id is required"}), 400
        inf_id = request_data['inf_id']
        logging.info(f"Received inference request with inf_id: {inf_id}")
        request_dict = {
            'inf_id': inf_id
        }

        data_hub_response = requests.post(f'{data_hub}/get_data', json=request_dict)
        if data_hub_response.status_code == 200:
            data_list = data_hub_response.json().get('file')
            # convert to numpy array
            data_np = np.array(data_list)
            data_np = data_np[:, 1:]
            data_len = data_np.shape[0]
            indices = np.linspace(0, data_len - 1, 200, dtype=int)
            data_np = data_np[indices]  

            # Step 3: Transpose to get (1, 3, 200)
            data_np = data_np.T[np.newaxis, ...]
            new_time_series_transform = minirocket.transform(data_np)
            decision_values = classifier.decision_function(new_time_series_transform)
            
            probabilities = torch.nn.functional.softmax(torch.tensor(decision_values), dim=1).numpy()

            top_k_indices = np.argsort(probabilities, axis=1)[:, -TOP_K:][:, ::-1]
            top_k_probabilities = np.sort(probabilities, axis=1)[:, -TOP_K:][:, ::-1]

            # Map indices to labels and create dictionary
            inverse_label_mapping = {v: k for k, v in label_mapping.items()}
            top_k_labels = np.vectorize(inverse_label_mapping.get)(top_k_indices)

            # Create dictionary of top-k predictions and probabilities
            top_k_dict = {str(label): float(prob) for label, prob in zip(top_k_labels[0], top_k_probabilities[0])} 
            
        else:
            print("Error:", data_hub_response.status_code, data_hub_response.text)
            return jsonify({"error": "Failed to get data from data hub"}), 500
        
        # get tensor list from data_hub response file
        
        response_time = time.time() - start_time
        logging.info(f"Response time: {response_time} seconds")
        result = {
            "metadata": {
                "inf_id": inf_id,
                "model_name": model_name,
                "version": version,
                "device_id": device_id,
                "instance_id": instance_id,
                "host": host,
                "port": port
            },
            "inference_result": top_k_dict,
            "response_time": response_time
        }
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error during inference: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"error": "An error occurred during inference"}), 500
    
if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Time series inference service")
    argparser.add_argument("--m", type=str, help="model name", default="mini_rocket")
    argparser.add_argument("--d", type=str, help="device", default="acc_phone_clip")
    argparser.add_argument("--t", type=bool, help="Test run", default=False)
    argparser.add_argument("--v", type=int, help="version", default=0)
    args = argparser.parse_args()
    model_name = args.m
    device = args.d
    test_run = args.t
    version = args.v
    app.run(host=host, port=port)

