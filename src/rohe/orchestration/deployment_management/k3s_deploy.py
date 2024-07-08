import argparse
import copy
import json
import os

import yaml

parser = argparse.ArgumentParser(description="Deployment application")
parser.add_argument(
    "--conf", help="configuration file", default="./application_config.json"
)
args = parser.parse_args()

# read temporary directory
os.system("rm ./deployed/*.yml")

deploy_conf = json.load(open(args.conf))

for app_key in deploy_conf:
    application_name = deploy_conf[app_key]
    for ser_key in application_name:
        service = application_name[ser_key]
        deploy_file = yaml.safe_load(open(service["dep_path"]))
        os.system("cp " + service["ser_path"] + " ./deployed/")
        print("Service Yaml is copied")

        for node in service["node"]:
            temp_file = copy.deepcopy(deploy_file)
            temp_file["metadata"]["name"] = temp_file["metadata"]["name"].replace(
                "node_name", node["node_name"]
            )

            if node["node_name"] == "all":
                temp_file["spec"]["template"]["spec"].pop("nodeSelector", None)
            else:
                temp_file["spec"]["template"]["spec"]["nodeSelector"][
                    "kubernetes.io/hostname"
                ] = temp_file["spec"]["template"]["spec"]["nodeSelector"][
                    "kubernetes.io/hostname"
                ].replace("node_name", node["node_name"])
            temp_file["spec"]["replicas"] = node["replicas"]
            with open(
                "./deployed/"
                + app_key
                + "-"
                + ser_key
                + "-"
                + node["node_name"]
                + ".yml",
                "w+",
            ) as outfile:
                yaml.dump(temp_file, outfile)
        print("Deployment files created")
os.system("sudo kubectl apply -f ./deployed/")

os.system("sudo kubectl get all -o wide")
