import argparse
import json
import os
import random
import time
from threading import Thread

import qoa4ml.qoaUtils as qoa_utils
import requests
from qoa4ml.reports import Qoa_Client


def init_env_variables():
    # Get Pod ID: for monitoring
    pod_id = os.environ.get("POD_ID")
    if not pod_id:
        print("POD_ID is not defined")
        pod_id = "Empty"
    # Get Node name: for monitoring
    node_name = os.environ.get("NODE_NAME")
    if not node_name:
        print("NODE_NAME is not defined")
        node_name = "Empty"
    # Get service url
    service_url = os.environ.get("SERVICE_URL")
    if not service_url:
        print("SERVICE_URL is not defined")
        service_url = "http://0.0.0.0:8000/"
    # Get configuration file
    conf_file = os.environ.get("CONF_FILE")
    if not conf_file:
        print("CONF_FILE is not defined")
        conf_file = "/conf.json"

    return {
        "pod_id": pod_id,
        "node_name": node_name,
        "service_url": service_url,
        "conf_file": conf_file,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument("--th", help="Number of thread", default=1)
    parser.add_argument("--sl", help="Sleep time", default=-1)
    parser.add_argument("--client", help="Client config file", default="./conf.json")
    args = parser.parse_args()
    env_var = init_env_variables()

    concurrent = int(args.th)
    time_sleep = float(args.sl)
    url = str(env_var["service_url"])
    conf_file = env_var["conf_file"]
    config_path = os.path.dirname(os.path.abspath(__file__))
    configuration = qoa_utils.load_config(config_path + conf_file)
    client_config = configuration["client_config"]
    connector_conf = configuration["connector_conf"]

    client_conf = configuration["client_app"]
    client_qoa_1 = Qoa_Client(client_config, connector_conf)
    client_qoa_1.init_report(
        client_conf["instance_id"] + "_1",
        client_conf["functionality"],
        client_conf["stage_id"] + "_1",
    )
    client_qoa_2 = Qoa_Client(client_config, connector_conf)
    client_qoa_2.init_report(
        client_conf["instance_id"] + "_2",
        client_conf["functionality"],
        client_conf["stage_id"] + "_2",
    )
    client_qoa_3 = Qoa_Client(client_config, connector_conf)
    client_qoa_3.init_report(
        client_conf["instance_id"] + "_3",
        client_conf["functionality"],
        client_conf["stage_id"] + "_3",
    )
    client_qoa_4 = Qoa_Client(client_config, connector_conf)
    client_qoa_4.init_report(
        client_conf["instance_id"] + "_4",
        client_conf["functionality"],
        client_conf["stage_id"] + "_4",
    )

    feedback_conf = client_config.copy()
    feedback_conf["role"] = "customer"
    client_qoa_5 = Qoa_Client(feedback_conf, connector_conf)
    client_qoa_5.init_report(
        client_conf["instance_id"] + "_5",
        client_conf["functionality"],
        client_conf["stage_id"] + "_5",
    )

    def sender(num_thread):
        count = 0
        error = 0
        start_time = time.time()
        while time.time() - start_time < 60000:
            try:
                client_qoa_1.timer()
                print("This is thread: ", num_thread, "Starting request: ", count)
                client_qoa_1.ex_set_metric("metric1", random.randint(1, 100))
                client_qoa_1.ex_set_metric("metric2", random.randint(1, 100))
                client_qoa_1.ex_observe_data_quality(
                    "image_width", random.randint(1, 100)
                )
                client_qoa_1.ex_observe_data_quality(
                    "image_height", random.randint(1, 100)
                )
                client_qoa_1.ex_observe_data_quality(
                    "object_width", random.randint(1, 100)
                )
                client_qoa_1.ex_observe_data_quality(
                    "object_height", random.randint(1, 100)
                )
                prediction_1 = client_qoa_1.ex_observe_confidence(
                    random.randint(0, 1), random.randint(1, 100) / 100
                )
                report_1 = client_qoa_1.report_external(client_qoa_1.timer())

                client_qoa_2.timer()
                client_qoa_2.ex_observe_data_quality(
                    "object_height", random.randint(1, 100)
                )
                prediction_2 = client_qoa_2.ex_observe_confidence(
                    random.randint(0, 1), random.randint(1, 100) / 100
                )
                report_2 = client_qoa_2.report_external(client_qoa_2.timer())

                client_qoa_3.timer()
                client_qoa_3.ex_observe_data_quality(
                    "object_height", random.randint(1, 100)
                )
                prediction_3 = client_qoa_3.ex_observe_confidence(
                    random.randint(0, 1), random.randint(1, 100) / 100
                )
                report_3 = client_qoa_3.report_external(client_qoa_3.timer())

                client_qoa_4.timer()
                client_qoa_4.get_reports(report_1)
                client_qoa_4.get_reports(report_2)
                client_qoa_4.get_reports(report_3)
                client_qoa_4.ex_observe_data_quality(
                    "object_height", random.randint(1, 100)
                )
                prediction_4 = client_qoa_4.ex_observe_confidence(
                    random.randint(0, 1),
                    random.randint(1, 100) / 100,
                    [prediction_1, prediction_2, prediction_3],
                )
                report_4 = client_qoa_4.report_external(client_qoa_4.timer(), True)
                if random.randint(1, 100) < 50:
                    client_qoa_5.timer()
                    client_qoa_5.ex_observe_accuracy(prediction_4, random.randint(0, 1))
                    report_5 = client_qoa_5.report_external(client_qoa_5.timer(), True)

                print("Thread - ", num_thread, " Response:", report_4)
                count += 1
                if time_sleep == -1:
                    time.sleep(1)
                else:
                    time.sleep(time_sleep)
            except Exception as e:
                error += 1
                print("[Error]: ", e)

    for i in range(concurrent):
        t = Thread(target=sender, args=[i])
        t.start()
