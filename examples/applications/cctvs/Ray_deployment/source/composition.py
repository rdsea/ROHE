import requests
from fastapi import FastAPI
from ray import serve
import json, cv2, os
import numpy as np
import os, time, uuid, ray
from qoa4ml.reports import Qoa_Client
import qoa4ml.qoaUtils as qoa_utils
import aggregation
from yolov8.yolov8 import Yolo8
from yolov5.yolov5 import Yolo5
import pymongo
from threading import Thread



def init_env_variables():
    # Get Pod ID: for monitoring
    pod_id = os.environ.get('POD_ID')
    if not pod_id:
        print("POD_ID is not defined")
        pod_id = "Empty"
    # Get Node name: for monitoring
    node_name = os.environ.get('NODE_NAME')
    if not node_name:
        print("NODE_NAME is not defined")
        node_name = "Empty"
    # Get Database Url
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL is not defined")
        database_url = "mongodb://195.148.22.62:27017/"
    # Get Database name
    database_name = os.environ.get('DATABASE_NAME')
    if not database_name:
        print("DATABASE_NAME is not defined")
        database_name = "object_detection_db"
    # Get user collection name
    user_collection_name = os.environ.get('USER_COLLECTION')
    if not user_collection_name:
        print("USER_COLLECTION is not defined")
        user_collection_name = "user_data"
    # Get instance collection name
    instance_collection_name = os.environ.get('INSTANCE_COLLECTION')
    if not instance_collection_name:
        print("INSTANCE_COLLECTION is not defined")
        instance_collection_name = "instance_data"
    # Get Customer id
    customer_id = os.environ.get('CUSTOMER_ID')
    if not customer_id:
        print("CUSTOMER_ID is not defined")
        customer_id = "Aaltosea1"
    # Get configuration file
    conf_file = os.environ.get('CONF_FILE')
    if not conf_file:
        print("CONF_FILE is not defined")
        conf_file = "/conf.json"
    
    return {
        "pod_id": pod_id,
        "node_name": node_name,
        "database_url": database_url,
        "database_name": database_name,
        "user_collection_name": user_collection_name,
        "instance_collection_name": instance_collection_name,
        "customer_id": customer_id,
        "conf_file": conf_file
    }
    
env_var = init_env_variables()

database_name = env_var["database_name"]
u_col_name = env_var["user_collection_name"]
i_col_name = env_var["instance_collection_name"]
conf_file = env_var["conf_file"]

mongo_client = pymongo.MongoClient(env_var["database_url"])


dblist = mongo_client.list_database_names()
if database_name not in dblist:
    print("The database {} not exists.".format(database_name))
object_detection_db = mongo_client[database_name]

collist = object_detection_db.list_collection_names()
if u_col_name in collist:
    print("The collection {} not exists.".format(u_col_name))
user_collection = object_detection_db[u_col_name]

last_updated_u_data = None
while True:
    u_query = {"id": env_var["customer_id"]}
    customer_data = user_collection.find(u_query).sort([('timestamp', pymongo.DESCENDING)])
    try:
        object_iterator = iter(customer_data)
        last_updated_u_data = object_iterator[0]
        break
    except TypeError as te:
        print(customer_data, ' is not iterable')
        time.sleep(10)
print("Downloading customer data success: ", last_updated_u_data)

config_path = os.path.dirname(__file__)
configuration = qoa_utils.load_config(config_path+conf_file)

client_config = configuration["client_config"]
connector_conf = configuration["connector_conf"]
stage_conf = configuration["stage_conf"]

@ray.remote
def enhance_image(image):
    enh_img_qoa = Qoa_Client(client_config,connector_conf)
    enh_img_conf = stage_conf["enhance_image"]
    enh_img_qoa.init_report(enh_img_conf["instanceID"], enh_img_conf["method"], enh_img_conf["stageID"])
    enh_img_qoa.timer()
    kernel = np.array([[0, -1, 0],
                   [-1, 5,-1],
                   [0, -1, 0]])
    enhanced_im = cv2.filter2D(src=image, ddepth=-1, kernel=kernel)
    responsetime = enh_img_qoa.timer()
    enh_img_qoa.ex_observe_data_quality("image_width", enhanced_im.shape[1])
    enh_img_qoa.ex_observe_data_quality("image_height", enhanced_im.shape[0])
    report = enh_img_qoa.report_external(responsetime)
    return enhanced_im, report

@ray.remote
def mean_aggregate(predictions):
    agg_prediction = aggregation.agg_mean(predictions)
    return agg_prediction

@ray.remote
def max_aggregate(predictions, report_list=[]):
    m_agg_qoa = Qoa_Client(client_config,connector_conf)
    m_agg_conf = stage_conf["max_aggregate"]
    m_agg_qoa.init_report(m_agg_conf["instanceID"], m_agg_conf["method"], m_agg_conf["stageID"])
    m_agg_qoa.timer()
    for report in report_list:
        m_agg_qoa.get_reports(report)
    agg_prediction = aggregation.agg_max(predictions)
    for obj in agg_prediction:
        for key in obj:
            m_agg_qoa.ex_observe_confidence(obj[key]["name"], obj[key]["confidence"])
    responsetime = m_agg_qoa.timer()
    report = m_agg_qoa.report_external(responsetime,submit=True)
    return agg_prediction, report


@serve.deployment()
class Yolo8Inference:
    def __init__(self, param):
        self.param = param
        self.model = Yolo8(param)
        self.qoa = Qoa_Client(client_config,connector_conf)
        self.conf = stage_conf["yolov5"]
        self.qoa.init_report(self.conf["instanceID"], self.conf["method"], self.conf["stageID"])

    def predict(self, image, report_list=[]):
        self.qoa.timer()
        for report in report_list:
            self.qoa.get_reports(report)
        prediction, pre_img = self.model.yolov8_inference(image)
        self.qoa.ex_observe_data_quality("n.o_object", len(prediction[self.param]))
        for pre in prediction[self.param]:
            for key in pre:
                for obj in pre[key]: 
                    self.qoa.ex_observe_confidence(obj["name"], obj["confidence"])
        responsetime = self.qoa.timer()
        report = self.qoa.report_external(responsetime)
        return {"prediction": prediction, "image": pre_img},report

@serve.deployment
class Yolo5Inference:
    def __init__(self, param):
        self.param = param
        self.model = Yolo5(param)
        self.qoa = Qoa_Client(client_config,connector_conf)
        self.conf = stage_conf["yolov8"]
        self.qoa.init_report(self.conf["instanceID"], self.conf["method"], self.conf["stageID"])


    def predict(self, image, report_list=[]):
        self.qoa.timer()
        for report in report_list:
            self.qoa.get_reports(report)
        prediction, pre_img = self.model.yolov5_inference(image)
        self.qoa.ex_observe_data_quality("n.o_object", len(prediction[self.param]))
        for pre in prediction[self.param]:
            for key in pre:
                for obj in pre[key]: 
                    self.qoa.ex_observe_confidence(obj["name"], obj["confidence"])
        responsetime = self.qoa.timer()
        report = self.qoa.report_external(responsetime)
        return {"prediction": prediction, "image": pre_img}, report



@serve.deployment
class Ensemble_ML:
    def __init__(self,model_list):
        self.models = model_list

    async def __call__(self, http_request):
        files = await http_request.form()
        image = await files["image"].read()
        user_data = await files["user_data"].read()
        print(json.loads(user_data))
        np_array = np.frombuffer(image, np.uint8)
        im = cv2.imdecode(np_array, cv2.IMREAD_COLOR) 
        en_im, en_report = await enhance_image.remote(im)
        response = {}
        predictions = {}
        last_predition = 0
        report_list = []
        response["prediction"]={}
        for model in self.models:
            result = await model.predict.remote(en_im,[en_report])
            predition,report = ray.get(result)
            predictions.update(predition["prediction"])
            last_predition = predition
            report_list.append(report)
        agg_pred, agg_report = await max_aggregate.remote(predictions,report_list)
        response["prediction"]["aggregated"] = agg_pred
        response["image"] = last_predition["image"]
        return response
        


if last_updated_u_data != None:
    instance_collection = object_detection_db[i_col_name]
    ensemble_model = last_updated_u_data["ensemble_model"]
    conf = [] 
    for model in ensemble_model:
        i_query = {"id": model}
        instance_data = instance_collection.find(i_query).sort([('timestamp', pymongo.DESCENDING)])
        try:
            object_iterator = iter(instance_data)
            last_updated_i_data = object_iterator[0]
            conf.append({"model":last_updated_i_data["model"],"parameter":last_updated_i_data["parameter"]})
            print("Add instance: ", last_updated_i_data)
        except TypeError as te:
            print(customer_data, ' is not iterable')
            time.sleep(10)
    print("Downloading ensemble composition success: ", conf)
    try:
        model_list = []
        for instance in conf:
            if instance["model"] == "Yolov5":
                model = Yolo5Inference.bind(instance["parameter"])
            if instance["model"] == "Yolov8":
                model = Yolo8Inference.bind(instance["parameter"]) 
            print("Adding instance: ", instance)
            model_list.append(model)
    except Exception as e:
        print("[Error]: {}".format(e))
    ensemble = Ensemble_ML.bind(model_list)

    serve.run(ensemble, host='0.0.0.0', port='8111')
