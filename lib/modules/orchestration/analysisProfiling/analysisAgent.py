import pymongo
import time
import pandas as pd
import random
import traceback,sys
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import matplotlib

from qoa4ml import qoaUtils
lib_path = qoaUtils.get_parent_dir(__file__,2)
sys.path.append(lib_path)
from roheObject import RoheObject

app = Flask(__name__)
api = Api(app)
matplotlib.use('Agg')


def get_dict_at(dict, i):
    keys = list(dict.keys())
    return dict[keys[i]], keys[i]

class Analysis_Agent(RoheObject):
    def __init__(self, conf_file, log_lev=2):
        super().__init__(logging_level=log_lev)
        self.conf = conf_file
        self.sample_rate = self.conf["sample_rate"]
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
                cpu_stats, key = get_dict_at(item["proc_cpu_stats"],0)
                mem_stats, key = get_dict_at(item["proc_mem_stats"],0)
                dict_start = {"cpu_user":cpu_stats["user"], "cpu_system":cpu_stats["system"],"mem_rss":mem_stats["rss"],"mem_vms":mem_stats["vms"]}
                new_row = pd.DataFrame.from_records([dict_start])
                output = pd.concat([output,new_row], ignore_index=True)
        except Exception as e:
            self.log("Error {} while handling resource report: ".format(type(e)),4)
            traceback.print_exception(*sys.exc_info())
        return output

    def handle_feedback(self, feedback_list):
        output = pd.DataFrame()
        try:
            if feedback_list:
                for item in feedback_list:
                    prediction, key = get_dict_at(item["prediction"],0)
                    if len(list(prediction["source"])):
                        dict_prediction = {"prediction":key, 
                                        "value":str(prediction["value"]),
                                        "confidence":prediction["confidence"],
                                        "source":list(prediction["source"]),
                                        "qoa_id":prediction["qoa_id"],
                                        "accuracy":prediction["accuracy"]}
                    
                        new_row = pd.DataFrame.from_records([dict_prediction])
                        output = pd.concat([output,new_row], ignore_index=True)
        except Exception as e:
            self.log("Error {} while handling feedback report: {}".format(type(e),e.__traceback__),4)
            traceback.print_exception(*sys.exc_info())
        return output

    def handle_quality_report(self, quality_report_list):
        output = pd.DataFrame()
        try:
            if quality_report_list:
                for item in quality_report_list:
                    dict_quality = {}
                    for stage in item["data_quality"]:
                        for metric in item["data_quality"][stage]:
                            for qoa_id in item["data_quality"][stage][metric]:
                                if "value" in item["data_quality"][stage][metric][qoa_id]:
                                    dict_quality[stage+"_"+metric+"_"+qoa_id] = item["data_quality"][stage][metric][qoa_id]["value"]
                    for stage in item["performance"]:
                        for metric in item["performance"][stage]:
                            for qoa_id in item["performance"][stage][metric]:
                                if "value" in item["performance"][stage][metric][qoa_id]:
                                    dict_quality[stage+"_"+metric+"_"+qoa_id] = item["performance"][stage][metric][qoa_id]["value"]
                    for index in range(len(item["prediction"])):
                        prediction, key = get_dict_at(item["prediction"],index)
                        dict_prediction = {"prediction":key, 
                                        "value":str(prediction["value"]),
                                        "confidence":prediction["confidence"],
                                        "source":list(prediction["source"]),
                                        "qoa_id":prediction["qoa_id"],
                                        "instance_id": item["execution_graph"]["instances"][prediction["qoa_id"]]["instance_id"]}
                        dict_prediction.update(dict_quality)
                        new_row = pd.DataFrame.from_records([dict_prediction])
                        output = pd.concat([output,new_row], ignore_index=True)
        except Exception as e:
            self.log("Error {} while handling service quality report: {}".format(type(e),e.__traceback__),4)
            traceback.print_exception(*sys.exc_info())
        self.log(output)
        return output
    

    def map_feedback(self, df_quality_report, df_feedback):
        output = pd.DataFrame()
        try: 
            if df_feedback.empty and not df_quality_report.empty:
                try:
                    for index, row in df_quality_report.iterrows():
                        if random.randint(1,100) < self.sample_rate:
                            row["accuracy"] = row["confidence"]
                            new_row = pd.DataFrame.from_records([row])
                            output = pd.concat([output,new_row], ignore_index=True)
                except IndexError as e:
                    self.log("Error while match accuracy (no feedback): {}".format(e),4)
                    traceback.print_exception(*sys.exc_info())
            else:
                for index, row in df_feedback.iterrows():
                    predictions = list(row["source"])
                    for prediction in predictions:
                        try:
                            df_filter = df_quality_report.loc[df_quality_report["prediction"] == prediction].to_dict(orient='records')
                            if len(df_filter):
                                q_row = df_filter[0]
                                if row["accuracy"] == 0: 
                                    q_row["accuracy"] = 0
                                else:
                                    q_row["accuracy"] = q_row["confidence"]
                                new_row = pd.DataFrame.from_records([q_row])
                                output = pd.concat([output,new_row], ignore_index=True) 
                        except IndexError as e:
                            self.log("Error while match accuracy: {}".format(e),4)
                            traceback.print_exception(*sys.exc_info())
        except Exception as e:
            self.log("Error {} while estimating feedback report: {}".format(type(e),e.__traceback__),4)
            traceback.print_exception(*sys.exc_info())
        return output
    

    def analyse(self):
        self.log(time.time())
        sumary = {}
        try:
            quality_report = self.quality_report_col.find().sort([('timestamp', pymongo.DESCENDING)])
            resource = self.resource_report_col.find().sort([('timestamp', pymongo.DESCENDING)])
            feedback = self.feedback_col.find().sort([('timestamp', pymongo.DESCENDING)])
        
            # if resource:
            #     print(resource)
            #     df_resource = self.handle_resource(list(resource))
            #     print(df_resource)
                # resource_util = self.aggreagate_resource(df_resource)
                # sumary["resource_utilization"] = resource_util

            if quality_report:
                df_quality_report = self.handle_quality_report(list(quality_report))
                self.log(df_quality_report.info())
                if not df_quality_report.empty:
                    sumary["total_prediction"] = len(df_quality_report.loc[df_quality_report["source"].str.len() != 0].index)
                else:
                    sumary["quality_report"] = "No quality reported"

            if feedback:
                df_feedback = self.handle_feedback(list(feedback))
                self.log(df_feedback.info())
                if not df_feedback.empty:
                    sumary["false_prediction"] = len(df_feedback.loc[df_feedback["accuracy"] == 0].index)
                    sumary["total_feedback"] = len(df_feedback.index)
                    sumary["service_accuracy"] = (1 - sumary["false_prediction"]/sumary["total_prediction"])*100
                else:
                    sumary["feed_back"] = "No feedback"

            df_mapped = self.map_feedback(df_quality_report, df_feedback)
            self.log(df_mapped)
            self.log(df_mapped.info())
            
            self.log(sumary)
            kmeans = KMeans(n_clusters=2)
            columns = df_mapped.columns
            clusters = kmeans.fit(df_mapped[['confidence', columns[10]]])

            df_mapped['Cluster'] = clusters.labels_
            self.log(df_mapped.info())

            plt.scatter(df_mapped['confidence'], df_mapped[columns[10]], c=clusters.labels_.astype(float), s=50, alpha=0.5)
            centroids = kmeans.cluster_centers_
            plt.scatter(centroids[:, 0], centroids[:, 1], c='red', s=50)
            plt.savefig('cluster.pdf')


        except Exception as e:
            self.log("Error {} while estimating contribution: {}".format(type(e),e.__traceback__),4)
            traceback.print_exception(*sys.exc_info())

class Analysis_Service(Resource):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        self.agent = kwargs["agent"]
        
    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})

    def post(self):
        if request.is_json:
            args = request.get_json(force=True)
            self.log(args)
            response = "Analyse metric"
            if (args['command'] == 0):
                self.agent.analyse()
            
            
        # get param from args here
        return jsonify({'status': "success", "response":response})

    def put(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': True})

    def delete(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': args})
