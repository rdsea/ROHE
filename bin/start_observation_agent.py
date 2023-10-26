import argparse, requests, json
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils

conf_path = ROHE_PATH+"/examples/agentConfig/"

headers = {
    'Content-Type': 'application/json'
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="dummy")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/agent")

    args = parser.parse_args()
    url = args.url

    config_file_path = conf_path+args.app+"/start.yaml"
    config_file = rohe_utils.load_config(config_file_path)

    response = requests.request("POST", url, headers=headers, data=json.dumps(config_file))
    print(response.json())