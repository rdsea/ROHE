from os import link
import argparse, json
from init_from_dag import generateDeployment
from profiling.profilingDeployment import profilingDeploy



if __name__ == '__main__':
    # Parse the input args
    parser = argparse.ArgumentParser(description="Profiling BTS Applicaiton")
    parser.add_argument('--conf', help='configuration file', default='./bts/profiling_config.json')
    args = parser.parse_args()

    profiling_config = json.load(open(args.conf))


    generateDeployment(profiling_config["user_config"], profiling_config["default_com_config"], profiling_config["default_deployment"])

    profilingDeploy(profiling_config["k3s_host"],profiling_config["k3s_port"], profiling_config["namespace"], profiling_config["profiling_time"], \
                    profiling_config["profiling_scales"], profiling_config["user_config"], key=None)
    
