from flask import Flask
from flask import request
from flask import Response
import requests as rq
import json 
from PIL import Image
import os, time, argparse, sys
from helpers.custom_logger import CustomLogger
import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient


qoa_conf_path = os.environ.get('QOA_CONF_PATH')
if not qoa_conf_path:
    qoa_conf_path = "./qoa_conf.json"

qoa_conf = qoa_utils.load_config(qoa_conf_path)
qoaClient = QoaClient(config_dict=qoa_conf)

from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

from core.common.restService import RoheRestService, ImageInferenceObject

logger = CustomLogger().get_logger()

def init_env_variables():
    service_name = os.environ.get('SERVICE_NAME')
    proc_port = os.environ.get("PREPROCESSOR_SERVICE_PORT")
    if not service_name:
        logger.error("SERVICE_NAME is not defined")
        service_name = "0.0.0.0"
        # service_name = "edge-preprocessor"
    if not proc_port:
        logger.error("PREPROCESSOR_SERVICE_PORT is not defined")
        proc_port= "5003"
        # port= "8000"
    return service_name, proc_port
    
class WebService(ImageInferenceObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        

    def imageProcessing(self, data):  
        try:
            qoaClient.timer() 
            json_data = {}
            image = data['image'] 
            qoaClient.timer()
            report = qoaClient.report()
       
            for i in range(10):
                r = rq.post(url=f"http://{self.conf['url']}:{self.conf['port']}/process", files = {'image' : image, 'report': json.dumps(report)})
                print(r)
                if (r!= None): 
                    break
                time.sleep(1)
               
            json_data = r.json()
            uid = json_data['uid']
            json_data["success"] = "true"
            # result = {}
        except Exception as e:
            logger.exception("Some Error occurred: {}".format(e)) 
            json_data = '{"error":"some error occurred in Web service"}'
        
        return json_data


if __name__ == '__main__': 
    # Load environment
    proc_url, proc_port = init_env_variables()
    config = {"url": proc_url, "port": proc_port}
    
    parser = argparse.ArgumentParser(description="Argument for Rohe Registration Service")
    parser.add_argument('--port', help='default port', default=5004)
    args = parser.parse_args()

    # Serving port
    port = int(args.port)

    # Load Rest service
    webService = RoheRestService(config)
    webService.add_resource(WebService, '/inference')
    webService.run(port=port)