from qoa4ml import qoaUtils as qoa_utils
import argparse, requests, json
import os, sys
main_path = config_file = qoa_utils.get_parent_dir(__file__,1)
sys.path.append(main_path)
import lib.roheUtils as rohe_utils
temp_path = main_path+"/temp"

headers = {
    'Content-Type': 'application/json'
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument('--app', help='application name', default="test")
    parser.add_argument('--url', help='registration url', default="http://localhost:5010/registration")

    args = parser.parse_args()
    url = args.url

    res_data = {"application": args.app}



    response = requests.request("POST", url, headers=headers, data=json.dumps(res_data))
    res_data["appID"] = response.json()["response"]["appID"]
    
    qoa_conf = {"client":res_data, "registration_url":args.url}
    qoa_conf["client"] = rohe_utils.load_qoa_conf_env(qoa_conf["client"])

    
    if rohe_utils.make_folder(temp_path):
        temp_path += ("/"+args.app)
        if rohe_utils.make_folder(temp_path):
            file_path = temp_path+"/qoa_config.yaml"
            rohe_utils.to_yaml(file_path, qoa_conf)
    
    
    print(qoa_conf)
    

        