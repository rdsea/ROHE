import argparse, requests, json
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils
temp_path = ROHE_PATH+"/temp"
template_path = ROHE_PATH+"/template"

headers = {
    'Content-Type': 'application/json'
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="test")
    parser.add_argument('--run', help='application name', default="experiment1")
    parser.add_argument('--client', help='application name', default="aaltosea1")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/registration")

    args = parser.parse_args()
    url = args.url

    res_data = {"appName": args.app}
    res_data["runID"] = args.run
    res_data["userID"] = args.client

    print(res_data)

    response = requests.request("POST", url, headers=headers, data=json.dumps(res_data))
    print(response.json())
    res_data["appID"] = response.json()["response"]["appID"]
    
    qoa_conf = {"client":res_data, "registration_url":args.url}
    qoa_conf["client"] = rohe_utils.load_qoa_conf_env(qoa_conf["client"])

    
    if rohe_utils.make_folder(temp_path):
        temp_path += ("/"+args.app)
        if rohe_utils.make_folder(temp_path):
            file_path = temp_path+"/qoa_config.yaml"
            rohe_utils.to_yaml(file_path, qoa_conf)
    
    print(qoa_conf)
    

        