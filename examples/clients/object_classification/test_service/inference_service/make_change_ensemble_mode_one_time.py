import requests
import json
import argparse
import os
import time
from datetime import datetime


# init_env_variables()
parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
parser.add_argument('--server_address', type= str, help='default service address', 
                    default= "http://localhost:30005/inference_service")
                    # default= "http://localhost:9000/inference_service")
                    # default= "http://127.0.0.1:39499/inference_service")
parser.add_argument('--ensemble_mode', type= int, help='ensemble mode', 
                    default= 1)

# Parse the parameters
args = parser.parse_args()
server_address = args.server_address
ensemble_mode = args.ensemble_mode

if ensemble_mode == 1:
    ensemble_mode = True
else:
    ensemble_mode = False


print(f"This is the ensemble mode: {ensemble_mode}")
# Prepare payload
payload = {
    'command': 'change_ensemble_mode',
    'local_file': True,
    'ensemble_mode': ensemble_mode,

}

# Make POST request to load new model
try:
    response = requests.post(server_address, data= payload)
    response_json = response.json()
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"At {timestamp}, this is the result of call for ensemble mode of {ensemble_mode}")
    if response.status_code == 200:
        # print(f"Success: {response_json.get('response')}")
        print(f"Success: {response_json}")
    else:
        # print(f"Failed: {response_json.get('error')}")
        print(f"Failed: {response_json}")

except Exception as e:
    print(f"An error occurred at client request side: {e}")


