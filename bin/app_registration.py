import argparse, requests, json
import sys, os, logging

# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils
temp_path = ROHE_PATH+"/temp"
template_path = ROHE_PATH+"/template"

headers = {
    'Content-Type': 'application/json'
}

# Specify parameter:
# --app: Application Name
# --run: Run/experiment name, id
# --user: User ID, who registrate the application
# --url: Link to the registration service
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="test")
    parser.add_argument('--run', help='Experiment name/id', default="experiment1")
    parser.add_argument('--user', help='application name', default="aaltosea1")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/registration")

    args = parser.parse_args()
    url = args.url

    res_data = {"appName": args.app}
    res_data["runID"] = args.run
    res_data["userID"] = args.user

    logging.debug(res_data)
    # Send registration data to registration service
    response = requests.request("POST", url, headers=headers, data=json.dumps(res_data))
    logging.debug(response.json())

    # get application ID from the registration service response
    res_data["appID"] = response.json()["response"]["appID"]
    
    # get QoA configuration from the registration service response
    qoa_conf = {"client":res_data, "registration_url":args.url}
    
    # Load metadata for QoA client from environment variable (optional)
    qoa_conf["client"] = rohe_utils.load_qoa_conf_env(qoa_conf["client"])

    # Save QoA configuration to file: /temp/<appName>/qoa_config.yaml 
    if rohe_utils.make_folder(temp_path):
        temp_path += ("/"+args.app)
        if rohe_utils.make_folder(temp_path):
            file_path = temp_path+"/qoa_config.yaml"
            rohe_utils.to_yaml(file_path, qoa_conf)
    
    logging.debug(qoa_conf)
    

        