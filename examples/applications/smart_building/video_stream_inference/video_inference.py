import torch
import argparse
import logging
import time
import traceback
from flask import Flask, request, jsonify
import duckdb
import socket
import uuid
import yaml
import os
import numpy as np
import requests
import pickle
import torch.nn.functional as F
from pytorchvideo.models.x3d import create_x3d
from pytorchvideo.models.hub import x3d_xs, x3d_s, x3d_m, x3d_l

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


config = yaml.safe_load(open("config.yaml"))
X3D_CONFIGS = config.get("model_config", {})
model_name = config.get("model_name", "x3d_xs")
test_run = config.get("test_run", False)
version = config.get("version", 0)
data_hub = config.get("data_hub", "http://localhost:5550")
DATA_SHAPE = config.get("data_shape", [1, 3, 4, 160, 160])
SAMPLE_LENGTH = DATA_SHAPE[2]
SAMPLE_CHANNELS = DATA_SHAPE[1]
SAMPLE_HEIGHT = DATA_SHAPE[3]
SAMPLE_WIDTH = DATA_SHAPE[4]
CLASS_LABEL = config.get("idx_to_label")
TOP_K = 10
NORM_MEAN = [0.45, 0.45, 0.45]
NORM_STD = [0.225, 0.225, 0.225]
INSTANCE_TABLE = "inference_service_instance"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

app = Flask(__name__)


def create_x3d_model(model_size, num_classes):
    """Create X3D model of specified size"""
    config = X3D_CONFIGS[model_size]
    # Create the model
    model = create_x3d(
        input_channel=3,
        input_clip_length=config['input_clip_length'],
        input_crop_size=config['input_crop_size'],
        model_num_class=num_classes
    ).to(DEVICE)
    return model

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
            return "127.0.0.1"

# DuckDB for testing
db_path = "../../database/"
db_dir = os.path.dirname(db_path)
db_file = os.path.join(db_dir, "file.duckdb")   
conn = duckdb.connect(db_file)

# get the hostname of the current machine
hostname = socket.gethostname()
print(f"Hostname: {hostname}")

# get ip address of current machine
ip_address = get_local_ip()
print(f"IP Address: {ip_address}")

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

print(f"Selected port: {port}")
host = ip_address
device_id = hostname


# Register the inference service instance in the database
conn.execute(f"""
INSERT INTO {INSTANCE_TABLE} (instance_id, model_id, model_version, device_id, ip_address, port, data)
VALUES ('{instance_id}', '{model_name}', '{version}', '{device_id}', '{ip_address}', {port}, 'None');
""")
conn.commit()
conn.close()

if test_run:
    # Load pretrained X3D model with model name and version online
    if model_name == "x3d_xs":
        model = x3d_xs(pretrained=True)
    elif model_name == "x3d_s":
        model = x3d_s(pretrained=True)
    elif model_name == "x3d_m":
        model = x3d_m(pretrained=True)
    elif model_name == "x3d_l":
        model = x3d_l(pretrained=True)
    else:
        raise ValueError(f"Model {model_name} is not supported.")
else:
    # load model from local path
    model_path = f"./model/{model_name}/v{version}/model.pth"
    # model size  is end of model_name upcase, split by underscore
    model_size = model_name.split('_')[-1].upper()
    num_classes = len(CLASS_LABEL)
    model = create_x3d_model(
        model_size=model_size,
        num_classes=num_classes
    )
    state_dict = torch.load(model_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

@app.route('/inference', methods=['POST'])
def inference():
    start_time = time.time()
    global model, classifier, label_mapping, data_hub, instance_id, model_name, version, device_id
    try:
        # get inf_id from request
        request_data = request.get_json()
        if not request_data or 'inf_id' not in request_data:
            return jsonify({"error": "inf_id is required"}), 400
        inf_id = request_data['inf_id']
        logging.info(f"Received inference request with inf_id: {inf_id}")
        
        # Pull data from data hub
        request_dict = {
            'inf_id': inf_id
        }
        data_hub_response = requests.post(f'{data_hub}/get_data', json=request_dict)
        if data_hub_response.status_code == 200:
            data = pickle.loads(data_hub_response.content)
            tensor_data = torch.tensor(data)
            logging.debug(f"Shape of tensor data: {tensor_data.shape}")
            tensor_data = tensor_data.permute(1, 0, 2, 3)  
            tensor_data = F.interpolate(tensor_data, size=(SAMPLE_HEIGHT, SAMPLE_WIDTH), mode='bilinear', align_corners=False)
            tensor_data = tensor_data.permute(1, 0, 2, 3)
            sample_size = tensor_data.shape[1] 
            logging.debug(f"Tensor shape after permute and resize: {tensor_data.shape}")
            # Normalize the tensor data using mean and std 
            tensor_data = tensor_data.float() / 255.0
            tensor_data = (tensor_data - torch.tensor(NORM_MEAN).view(3, 1, 1, 1)) / torch.tensor(NORM_STD).view(3, 1, 1, 1)

            if sample_size < SAMPLE_LENGTH:
                # If the sample size is smaller than the required length, pad the tensor
                padding = SAMPLE_LENGTH - sample_size
                tensor_data = F.pad(tensor_data, (0, padding), "constant", 0)
            elif sample_size > SAMPLE_LENGTH:
                # If the sample size is larger than the required length, sample uniformly
                indices = np.linspace(0, sample_size - 1, SAMPLE_LENGTH).astype(int)
                tensor_data = tensor_data[:, indices, :, :]
            logging.debug(f"Shape of tensor data after sampling: {tensor_data.shape}")
            tensor_data = tensor_data.unsqueeze(0)  # Add batch dimension
            logging.debug(f"Shape of tensor data after adding batch dimension: {tensor_data.shape}")

            # Perform inference on GPU
            with torch.no_grad():
                model.eval()
                tensor_data = tensor_data.to(DEVICE)
                output = model(tensor_data)
                output = output.cpu()
                logging.debug(f"Shape of model output: {output.shape}")

            # Get top-k predictions
            top_k = torch.topk(output, TOP_K, dim=1)
            top_k_indices = top_k.indices.squeeze(0).tolist()
            top_k_scores = top_k.values.squeeze(0).tolist()
            top_k_dict = {CLASS_LABEL[str(idx)]: score for idx, score in zip(top_k_indices, top_k_scores)}
            logging.info(f"Top {TOP_K} predictions: {top_k_dict}")
            
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
            
        else:
            print("Error:", data_hub_response.status_code, data_hub_response.text)
            return jsonify({"error": "Failed to get data from data hub"}), 500
        
    except Exception as e:
        logging.error(f"Error during inference: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"error": "An error occurred during inference"}), 500
    
if __name__ == '__main__':
    app.run(host=host, port=port)

