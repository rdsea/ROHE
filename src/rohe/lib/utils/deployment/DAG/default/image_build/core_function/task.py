import argparse
import json

from .task_handler import TaskHandler

if __name__ == "__main__":
    # Parse the input args
    parser = argparse.ArgumentParser(description="Data processing")
    parser.add_argument("--conf", help="configuration file", default="./config.json")
    parser.add_argument("--next_ip", help="next destination ip", required=False)
    parser.add_argument("--next_port", help="next destination ip", required=False)
    args = parser.parse_args()
    config_data = json.load(open(args.conf))
    if args.next_ip is not None:
        config_data["sender"][0]["configuration"]["url"] = (
            "tcp://" + args.next_ip + ":" + args.next_port
        )
    task = TaskHandler(config_data)
    print("start the loop")
    task.run()
