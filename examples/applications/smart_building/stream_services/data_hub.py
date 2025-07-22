from flask import Flask, request, jsonify, send_file, make_response

import logging
import uuid
import sys
import torch
import os
import argparse
# import duckdb
import yaml
import pandas as pd
import random
import gzip
import pickle
import io

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from stream_handler.stream_handler import ModalityType

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)
from stream_handler.stream_handler import StreamHandler, DataType, ModelFamily, MAX_BUFFER_WINDOW, DEFAULT_FRAME_RATE
app = Flask(__name__)



stream_dict = {}
current_used_port = 0
DEFAULT_CONFIG = '../config/data_hub.yaml'
data_hub_config = {}
inf_list = []
performance_df = None
file_id_dict = {}

def load_config():
    global data_hub_config, performance_df
    # Load config
    if os.path.exists(DEFAULT_CONFIG):
        with open(DEFAULT_CONFIG, 'r') as stream:
            try:
                data_hub_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                logging.error(exc)
    else:
        logging.error("No config file found")
        

@app.route('/add_stream_handler', methods=['POST'])
def add_stream_handler():
    global stream_dict, current_used_port, data_hub_config
    # Get request data
    request_data = request.get_json()
    data_type = request_data.get('data_type', DataType.VIDEO.value)
    data_shape = request_data.get('data_shape', [3, 0, 240, 320])
    sample_index = request_data.get('sample_index', 1)
    model_family = request_data.get('model_family', ModelFamily.X3D.value)
    stream_id = request_data.get('stream_id', str(uuid.uuid4()))
    modality = request_data.get('modality', 0)
    host = request_data.get('host', 'localhost')
    
    # Check if stream_id exists
    if stream_id in stream_dict:
        return jsonify({'error': 'stream_id already exists'}), 400
    
    # allocate new port
    port = data_hub_config["start_port"] + current_used_port
    current_used_port += 1
    
    # Create a new StreamHandler instance
    i_stream = StreamHandler(host=host, port=port, data_type=data_type, data_shape=data_shape, sample_index=sample_index, model_family=model_family,buffer_size=MAX_BUFFER_WINDOW, frame_rate=DEFAULT_FRAME_RATE, stream_id=stream_id, modality=modality)
    stream_dict[i_stream.stream_id] = i_stream
    i_stream.start_consume()
    logging.info(f"Stream handler {i_stream.stream_id} started at port {port}")
    return jsonify({'port': port, 'stream_id': i_stream.stream_id}), 200

@app.route('/query_data', methods=['POST'])
def query_data():
    global stream_dict, inf_list, file_id_dict
    
    # Get request data
    request_data = request.get_json()
    
    # Get time window and stream ID from request
    time_window = request_data.get('time_window', 1)
    stream_id = request_data.get('stream_id', None)
    inf_id = request_data.get('inf_id', None)
    
    # Check if stream_id is provided and exists in stream_dict
    if stream_id == None:
        return jsonify({'error': 'stream_id is required'}), 400
    if stream_id not in stream_dict:
        return jsonify({'error': 'stream_id not found'}), 400
    
    # Get data from stream
    i_stream = stream_dict[stream_id]
    window_data = i_stream.process_data(time_window)
    modality = i_stream.modality
    
    # Check if window_data is None
    if window_data == None:
        return jsonify({'error': 'Error in processing data'}), 500
    
    # Save data to tmp folder instead of keep in memory to avoid memory overflow
    # inf_data = random.choice(inf_list)
    
   
    if inf_id is None:
        inf_id = str(uuid.uuid4())
        
    # only for testing
    inf_label = str(random.randint(0, 35))
    # inf_id = inf_data[0]
    # inf_label = inf_data[1]
    
    # if ../temp/ does not exist, create it
    if not os.path.exists('../tmp'):
        os.makedirs('../tmp')
        
    
    # Save the tensor to the file
    if modality == ModalityType.VIDEO.value:
        # Save window_data to file
        file_path = f"../tmp/{stream_id}_{inf_id}.pt.gz"
        # print max vaule of window_data
        logging.info(f"Max value of window_data: {window_data.max()}")
        window_int_data = (window_data * 255).clamp(0, 255).to(torch.uint8)
        with gzip.open(file_path, 'wb') as f:
            pickle.dump(window_int_data, f, protocol=4)
    else:
        # Save window_data to file
        file_path = f"../tmp/{stream_id}_{inf_id}.pt"
        torch.save(window_data, file_path)
    
    # Add file information to file_id_dict
    file_id_dict[inf_id] = {"file_path": file_path, "access_count": 0}
    
    # min_inf_time, max_inf_time, avg_inf_time = get_t_profile_by_modality(int(modality)) 
    return jsonify({'success': True, 'inf_id': inf_id, 'shape': window_data.shape, 'modality': modality}), 200

@app.route('/get_data', methods=['POST'])
def get_data():
    
    # File management
    global file_id_dict, data_hub_config
    no_ensemble = data_hub_config.get('no_ensemble', 2)

    # Get file ID from request
    request_data = request.get_json()
    inf_id = request_data.get('inf_id', None)
    no_ensemble = request_data.get('ensemble_size', no_ensemble)

    # Check if file ID is provided
    if inf_id == None:
        return jsonify({'error': 'No inference ID'}), 400

    # Check if file ID exists in the dictionary
    file_dict = file_id_dict.get(inf_id, None)
    
    if file_dict is None:
        return jsonify({'error': 'File ID not found'}), 404
    
    # Check if file_path exists in the dictionary
    file_path = file_dict.get('file_path', None)
    
    # Check if file has been accessed more than NO_ENSEMBLE times
    access_count = file_dict.get('access_count', 0) 
    
    # Increment access count
    file_id_dict[inf_id]['access_count'] = access_count + 1
    
    # If access count exceeds no_ensemble, delete the file
    delete_file = False
    if file_id_dict[inf_id]['access_count'] >= no_ensemble:
        delete_file = True

    # If file_path is None, return error
    if file_path == None:
        return jsonify({'error': 'File not found'}), 404

    # Load data from file
    if file_path.endswith('.gz'):
        # send bytes data
        with open(file_path, 'rb') as f:
            gz_bytes = f.read()

        response = make_response(send_file(
            io.BytesIO(gz_bytes),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name="window_data.pt.gz"
        ))
        response.headers["Content-Encoding"] = "gzip"
        if delete_file:
            os.remove(file_path)
            del file_id_dict[inf_id]
            logging.info(f"File {file_path} deleted after {no_ensemble} accesses")
        return response
    else:
        data = torch.load(file_path)
        # Convert tensor to list
        data_list = data.tolist()
        
        # If delete_file is True, remove the file and delete the entry from file_id_dict
        if delete_file:
            os.remove(file_path)
            del file_id_dict[inf_id]
            logging.info(f"File {file_path} deleted after {no_ensemble} accesses")
            
        return jsonify({'success': True, 'file': data_list, 'shape': data.shape}), 200
    

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="Control Plane")
    argparser.add_argument("--p", type=int, help="port", default=5550)
    argparser.add_argument("--h", type=str, help="host", default="0.0.0.0")
    args = argparser.parse_args()
    host = args.h
    port = args.p
    load_config()
    app.run(host=host, port=port)