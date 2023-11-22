import argparse, requests, json
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils

# set default configuration path
conf_path = ROHE_PATH+"/examples/agentConfig/"
# set default header
headers = {
    'Content-Type': 'application/json'
}


# Specify parameter:
# --app: Application Name
# --conf: path to agent configuration
# --url: Link to the agent service
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="dummy")
    parser.add_argument('--conf', help='configuration path', default="")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/agent")

    args = parser.parse_args()
    url = args.url

    if args.conf == "":
        config_file_path = conf_path+args.app+"/stop.yaml"
    else:
        config_file_path = args.conf
    
    # load stop command from path
    config_file = rohe_utils.load_config(config_file_path)
    # send stop command to agent service
    response = requests.request("POST", url, headers=headers, data=json.dumps(config_file))
    print(response.json())