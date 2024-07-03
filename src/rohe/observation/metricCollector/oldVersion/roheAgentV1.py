import json
import os
import random
import sys
import time
import traceback
from threading import Thread, Timer

import pandas as pd
import pymongo
from flask import jsonify, request
from flask_restful import Resource
from qoa4ml.collector.amqp_collector import Amqp_Collector


def get_dict_at(dict, i):
    keys = list(dict.keys())
    return dict[keys[i]], keys[i]


class ObservabilityAgent:
    def __init__(self, conf_file):
        self.conf = conf_file
        colletor_conf = self.conf["collector"]
        self.sample_rate = self.conf["sample_rate"]
        self.false_rate = self.conf["false_rate"]
        self.false_count = 0
        self.collector = Amqp_Collector(
            colletor_conf["amqp_collector"]["conf"], host_object=self
        )
        db_conf = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(db_conf["url"])
        self.db = self.mongo_client[db_conf["db_name"]]
        self.quality_report_col = self.db[db_conf["quality_report_col"]]
        self.quality_temp_col = self.db[db_conf["quality_temp_col"]]
        self.resource_report_col = self.db[db_conf["resource_report_col"]]
        self.resource_temp_col = self.db[db_conf["resource_temp_col"]]
        self.feedback_col = self.db[db_conf["feedback_col"]]
        self.feedback_temp_col = self.db[db_conf["feedback_temp_col"]]
        self.insert_db = True
        self.timer = None

    def handle_resource(self, resource_list):
        output = pd.DataFrame()
        try:
            for item in resource_list:
                cpu_stats, key = get_dict_at(item["proc_cpu_stats"], 0)
                mem_stats, key = get_dict_at(item["proc_mem_stats"], 0)
                dict_start = {
                    "cpu_user": cpu_stats["user"],
                    "cpu_system": cpu_stats["system"],
                    "mem_rss": mem_stats["rss"],
                    "mem_vms": mem_stats["vms"],
                }
                new_row = pd.DataFrame.from_records([dict_start])
                output = pd.concat([output, new_row], ignore_index=True)
        except Exception as e:
            print(f"[ERROR] - Error {type(e)} while handling resource report: ")
            traceback.print_exception(*sys.exc_info())
        return output

    def handle_feedback(self, feedback_list):
        output = pd.DataFrame()
        try:
            if feedback_list:
                print(feedback_list)
                for item in feedback_list:
                    prediction, key = get_dict_at(item["prediction"], 0)
                    dict_prediction = {
                        "prediction": key,
                        "value": str(prediction["value"]),
                        "confidence": prediction["confidence"],
                        "source": list(prediction["source"]),
                        "qoa_id": prediction["qoa_id"],
                        "accuracy": prediction["accuracy"],
                    }
                    new_row = pd.DataFrame.from_records([dict_prediction])
                    output = pd.concat([output, new_row], ignore_index=True)
        except Exception as e:
            print(
                f"[ERROR] - Error {type(e)} while handling feedback report: {e.__traceback__}"
            )
            traceback.print_exception(*sys.exc_info())
        return output

    def handle_quality_report(self, quality_report_list):
        output = pd.DataFrame()
        try:
            if quality_report_list:
                for item in quality_report_list:
                    for index in range(len(item["prediction"])):
                        prediction, key = get_dict_at(item["prediction"], index)
                        dict_prediction = {
                            "prediction": key,
                            "value": str(prediction["value"]),
                            "confidence": prediction["confidence"],
                            "source": list(prediction["source"]),
                            "qoa_id": prediction["qoa_id"],
                            "instance_id": item["execution_graph"]["instances"][
                                prediction["qoa_id"]
                            ]["instance_id"],
                        }
                        new_row = pd.DataFrame.from_records([dict_prediction])
                        output = pd.concat([output, new_row], ignore_index=True)
        except Exception as e:
            print(
                f"[ERROR] - Error {type(e)} while handling service quality report: {e.__traceback__}"
            )
            traceback.print_exception(*sys.exc_info())
        print(output)
        return output

    def aggreagate_resource(self, df_resource):
        output = {}
        try:
            if not df_resource.empty:
                output = {
                    "mean_cpu_user": df_resource["cpu_user"].mean(),
                    "mean_cpu_system": df_resource["cpu_system"].mean(),
                    "avg_mem_rss": df_resource["mem_rss"].mean(),
                    "avg_mem_vms": df_resource["mem_vms"].mean(),
                }
                return output
        except Exception as e:
            print(
                f"[ERROR] - Error {type(e)} while estimating resource report: {e.__traceback__}"
            )
            traceback.print_exception(*sys.exc_info())
        return "No resource usage reported"

    def estimate_feedback(self, df_quality_report, df_feedback):
        output = pd.DataFrame()
        try:
            if df_feedback.empty and not df_quality_report.empty:
                try:
                    for _index, row in df_quality_report.iterrows():
                        if random.randint(1, 100) < self.sample_rate:
                            row["accuracy"] = row["confidence"]
                            new_row = pd.DataFrame.from_records([row])
                            output = pd.concat([output, new_row], ignore_index=True)
                except IndexError as e:
                    print("Error while match accuracy (no feedback): ", e)
                    traceback.print_exception(*sys.exc_info())
            else:
                for _index, row in df_feedback.iterrows():
                    predictions = list(row["source"])
                    for prediction in predictions:
                        try:
                            df_filter = df_quality_report.loc[
                                df_quality_report["prediction"] == prediction
                            ].to_dict(orient="records")
                            if len(df_filter):
                                q_row = df_filter[0]
                                if q_row["value"] == row["value"]:
                                    q_row["accuracy"] = row["accuracy"]
                                elif row["accuracy"] == 0:
                                    q_row["accuracy"] = 1
                                else:
                                    q_row["accuracy"] = 0
                                new_row = pd.DataFrame.from_records([q_row])
                                output = pd.concat([output, new_row], ignore_index=True)
                        except IndexError as e:
                            print("Error while match accuracy: ", e)
                            traceback.print_exception(*sys.exc_info())
        except Exception as e:
            print(
                f"[ERROR] - Error {type(e)} while estimating feedback report: {e.__traceback__}"
            )
            traceback.print_exception(*sys.exc_info())
        return output

    def contribution_calculator(self, row, penalty):
        if int(row["accuracy"]) == 0 and int(row["value"]) == 1:
            row["contribution"] = -row["confidence"]
        elif int(row["accuracy"]) == 0 and int(row["value"]) == 0:
            row["contribution"] = -penalty * row["confidence"]
        elif (
            int(row["accuracy"]) == 1
            and int(row["value"]) == 1
            or int(row["accuracy"]) == 1
            and int(row["value"]) == 0
        ):
            row["contribution"] = row["confidence"]
        return row

    def estimate_contribution(self):
        print(time.time())
        summary = {}
        try:
            quality_report = self.quality_temp_col.find().sort(
                [("timestamp", pymongo.DESCENDING)]
            )
            resource = self.resource_temp_col.find().sort(
                [("timestamp", pymongo.DESCENDING)]
            )
            feedback = self.feedback_temp_col.find().sort(
                [("timestamp", pymongo.DESCENDING)]
            )

            if resource:
                df_resource = self.handle_resource(list(resource))
                resource_util = self.aggreagate_resource(df_resource)
                summary["resource_utilization"] = resource_util

            if quality_report:
                df_quality_report = self.handle_quality_report(list(quality_report))
                if not df_quality_report.empty:
                    summary["total_prediction"] = len(
                        df_quality_report.loc[
                            df_quality_report["source"].str.len() != 0
                        ].index
                    )
                else:
                    summary["quality_report"] = "No quality reported"

            if feedback:
                df_feedback = self.handle_feedback(list(feedback))
                if not df_feedback.empty:
                    summary["false_prediction"] = len(
                        df_feedback.loc[df_feedback["accuracy"] == 0].index
                    )
                    summary["total_feedback"] = len(df_feedback.index)
                    summary["service_accuracy"] = (
                        1 - summary["false_prediction"] / summary["total_prediction"]
                    ) * 100
                else:
                    summary["feed_back"] = "No feedback"

            df_contr = self.estimate_feedback(df_quality_report, df_feedback)
            if len(df_contr.index) == 0:
                print("No Feedback")
            else:
                df_contr = df_contr.apply(
                    lambda row: self.contribution_calculator(row, 10), axis=1
                )
                print(df_contr)
                df_con = df_contr.groupby("instance_id")["contribution"].sum()
                print(df_con)
                summary["contribution"] = df_con.to_dict()
                config_path = os.path.dirname(os.path.abspath(__file__))
                output_folder = config_path + self.conf["output_folder"]
                json_object = json.dumps(summary, indent=4)
                with open(
                    output_folder + "sumary_at_" + str(time.time()) + ".json", "w"
                ) as outfile:
                    outfile.write(json_object)
            self.reset_temp_db()

            print(summary)
            self.false_count = 0
            self.timer = Timer(self.conf["timer"], self.estimate_contribution)
            self.timer.start()

        except Exception as e:
            print(
                f"[ERROR] - Error {type(e)} while estimating contribution: {e.__traceback__}"
            )
            traceback.print_exception(*sys.exc_info())

    def reset_db(self):
        self.quality_report_col.drop()
        self.quality_temp_col.drop()
        self.resource_report_col.drop()
        self.resource_temp_col.drop()
        self.feedback_col.drop()
        self.feedback_temp_col.drop()

    def reset_temp_db(self):
        self.quality_temp_col.drop()
        self.resource_temp_col.drop()
        self.feedback_temp_col.drop()

    def start_consuming(self):
        print("Start Consuming")
        self.collector.start()

    def start(self):
        sub_thread = Thread(target=self.start_consuming)
        sub_thread.start()
        self.timer = Timer(self.conf["timer"], self.estimate_contribution)
        self.timer.start()

    def categorize_report(self, report):
        if "execution_graph" in report:
            if report["role"] == "mlprovider":
                return 1  # quality report
            elif report["role"] == "customer":
                return 2  # feedback report
            else:
                return 0  # unknown
        elif "proc_cpu_stats" in report:
            return 3  # resource monitoring report
        else:
            return 0  # unknown

    def check_feedback(self, mess):
        prediction, key = get_dict_at(mess["prediction"], 0)
        if prediction["accuracy"] == 0:
            self.false_count += 1
            if self.false_count > self.false_rate:
                self.timer.cancel()
                self.estimate_contribution()

    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))
        category = self.categorize_report(mess)
        if self.insert_db:
            if category == 1:  # quality report
                insert_id = self.quality_report_col.insert_one(mess)
                print("Receive a quality report: ", insert_id)
                insert_id = self.quality_temp_col.insert_one(mess)
                print("Insert to database", insert_id)
            elif category == 2:  # feedback report
                insert_id = self.feedback_col.insert_one(mess)
                self.check_feedback(mess)
                print("Receive a feedback report: ", insert_id)
                insert_id = self.feedback_temp_col.insert_one(mess)
                print("Insert to database", insert_id)
            elif category == 3:  # resource monitoring report
                insert_id = self.resource_report_col.insert_one(mess)
                print("Receive a resource monitoring report: ", insert_id)
                insert_id = self.resource_temp_col.insert_one(mess)
                print("Insert to database", insert_id)
            else:
                print("Unknown report: ", mess)

    def stop(self):
        # self.collector.stop()
        self.insert_db = False

    def restart(self):
        # self.collector.stop()
        self.insert_db = True

    def update_conf(self, args):
        self.conf["timer"] = args["timer"]
        self.conf["sample_rate"] = args["sample_rate"]
        self.false_rate = args["false_rate"]


class AgentService(Resource):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        self.agent = kwargs["agent"]

    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({"status": args})

    def post(self):
        if request.is_json:
            args = request.get_json(force=True)
            print(args)
            """
            Action table:
            0 - start the agent
            {
                "command": 0
            }
            1 - reset database
            Example:
            {
                "command": 1
            }
            2 - stop consume message
            Example:
            {
                "command": 2
            }
            3 - restart consume message
            Example:
            {
                "command": 3
            }
            4 - update configuration
            {
                "command"
            }
            """
            response = "false"
            if args["command"] == 0:
                self.agent.start()
                response = "Agent started"
            elif args["command"] == 1:
                self.agent.reset_db()
                response = "Database is reset"
            elif args["command"] == 2:
                self.agent.stop()
                response = "Agent stop consume message"
            elif args["command"] == 3:
                self.agent.restart()
                response = "Agent restart consume message"
            elif args["command"] == 4:
                self.agent.update_conf(args)
                response = "Agent configuration updated"

        # get param from args here
        return jsonify({"status": "success", "response": response})

    def put(self):
        # if request.is_json:
        #     args = request.get_json(force=True)
        # get param from args here
        return jsonify({"status": True})

    def delete(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({"status": args})
