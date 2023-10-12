from qoa4ml import qoaUtils as qoa_utils
import argparse, requests, json
import os, sys
main_path = config_file = qoa_utils.get_parent_dir(__file__,2)
sys.path.append(main_path)
conf_path = main_path+"/examples/agentConfig/"

headers = {
    'Content-Type': 'application/json'
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="dummy")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/agent")

    args = parser.parse_args()
    url = args.url

    config_file_path = conf_path+args.app+"/stop.yaml"
    config_file = qoa_utils.load_config(config_file_path)

    response = requests.request("POST", url, headers=headers, data=json.dumps(config_file))
    print(response.json())