from os import link
import argparse, json
from init_from_dag import generateDeployment
from profiling.profilingDeployment import profilingDeploy

##TODO this program should be generic for any example, not for specific BTS, we need to refactor it

if __name__ == '__main__':
    # Parse the input args
    parser = argparse.ArgumentParser(description="Profiling BTS Applicaiton")
    parser.add_argument('--conf', help='configuration file', default='./bts/profiling_config.json')
    parser.add_argument('--output_file',help='deployment out put file')
    parser.add_argument('--deployment',help='yes if the deployment is also carried out')
    args = parser.parse_args()

    profiling_config = json.load(open(args.conf))
    deployment_mode =(args.deployment is not None)
    output_file =args.output_file
    generateDeployment(profiling_config["user_config"], profiling_config["default_com_config"], profiling_config["default_deployment"])
    if deployment_mode:

        profilingDeploy(profiling_config["k3s_host"],profiling_config["k3s_port"], profiling_config["namespace"], profiling_config["profiling_time"], \
                        profiling_config["profiling_scales"], profiling_config["user_config"], key=None)
        
