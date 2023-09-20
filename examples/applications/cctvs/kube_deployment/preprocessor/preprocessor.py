from flask import Flask
from flask import request
from flask import Response
from PIL import Image, ImageEnhance
from io import BytesIO
import requests as rq
import uuid
import json, time
import os
import cv2, sys, argparse
import numpy as np
from helper.custom_logger import CustomLogger
import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient


qoa_conf_path = os.environ.get('QOA_CONF_PATH')
if not qoa_conf_path:
    qoa_conf_path = "./qoa_conf.json"


qoa_conf = qoa_utils.load_config(qoa_conf_path)
qoaClient = QoaClient(config_dict=qoa_conf)

lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5

main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)
from lib.services.restService import ImageInferenceObject, RoheRestService
logger = CustomLogger().get_logger()



def init_env_variables():
    edge_inference_service_name = os.environ.get('EDGE_INFERENCE_SERVICE_NAME')
    edge_inference_port = os.environ.get("EDGE_INFERENCE_PREPROCESSOR_SERVICE_PORT")
    if not edge_inference_service_name:
        logger.error("EDGE_INFERENCE_SERVICE_NAME is not defined")
        edge_inference_service_name = "127.0.0.1"
        # edge_inference_service_name = "edge-inference-service"

    if not edge_inference_port:
        logger.error("EDGE_INFERENCE_PREPROCESSOR_SERVICE_PORT is not defined")
        edge_inference_port= "5002"
        # edge_inference_port = "4002"
    return edge_inference_service_name, edge_inference_port



class ProcessService(ImageInferenceObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs

    
    def imageProcessing(self, data):
        try:
            qoaClient.timer()  
            image = data['image'] 
            pReport = data['report'] 
            qoaClient.importPReport(pReport)
            json_data = {}
            job_id = uuid.uuid4().hex
            np_array = np.frombuffer(image, np.uint8)
            im = cv2.imdecode(np_array, cv2.IMREAD_COLOR) 
            qoaClient.observeMetric("image_width", im.shape[0], 1)
            qoaClient.observeMetric("image_height", im.shape[1], 1)
            data = preprocess(im)
            qoaClient.timer()
            report = qoaClient.report()
            for i in range(10):
                r = rq.post(url=f"http://{self.conf['url']}:{self.conf['port']}/inference", files = {'image' : image, 'report': json.dumps(report)})
                if (r!= None): 
                    break
                time.sleep(0.1)
            json_data = {"data":json.loads(r.content)}
            json_data['uid'] = job_id
        except Exception as e:
            logger.exception("Some Error occurred: {}".format(e)) 
            json_data = '{"error":"some error occurred in Processing service"}'
        
        return json_data

def preprocess(img):
    # enhancer = ImageEnhance.Sharpness(img)
    # enhanced_im = enhancer.enhance(1.2)
    kernel = np.array([[0, -1, 0],
                   [-1, 5,-1],
                   [0, -1, 0]])
    enhanced_im = Image.fromarray(cv2.filter2D(src=img, ddepth=-1, kernel=kernel))

    byte_io = BytesIO()
    enhanced_im.save(byte_io, 'JPEG')
    byte_io.seek(0)
    return byte_io




if __name__ == '__main__':
    inf_url, inf_port = init_env_variables()
    config = {"url": inf_url, "port": inf_port}
    parser = argparse.ArgumentParser(description="Argument for Rohe Registration Service")
    parser.add_argument('--port', help='default port', default=5003)
    args = parser.parse_args()

    
    # Serving port
    port = int(args.port)


    # Load model


    # Load Rest service
    procService = RoheRestService(config)
    procService.add_resource(ProcessService, '/process')
    procService.run(port=port)