import argparse
from flask import request
from flask import Response
import sys, json, io, os
import aggregation
import numpy as np
from PIL import Image
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

from lib.services.restService import ImageInferenceObject
from lib.services.yoloService import YoloRestService



class MLInferenceObject(ImageInferenceObject):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        # Load configuration 
        self.conf = kwargs
        self.models = self.conf["models"]


    def imageProcessing(self, data):  
        try:    
            qoaClient.timer()  
            image = data['image'] 
            pReport = data['report'] 
            qoaClient.importPReport(pReport) 
            json_data = {}     
        
            predictions = {}
            # Load Image from request
            image = np.array(Image.open(io.BytesIO(image)))
            
            # Prediction from model composition
            for model in self.models:
                result,report = model.predict(image)
                predictions.update(result["prediction"])
                
            # Aggreagte result
            json_data = aggregation.agg_max(predictions)
            for ob in json_data:
                key = list(ob.keys())[0]
                object_name = ob[key]["name"]
                confidence = ob[key]["confidence"]
                # print(object_name, confidence)
                qoaClient.observeInferenceMetric("confidence_"+object_name, confidence)
            
        except Exception as e:
            json_data = '{"error":"some error occurred in Inference service"}'
        qoaClient.timer()
        report = qoaClient.report(submit=True)
        return json_data
        

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Registration Service")
    parser.add_argument('--conf', help='configuration file of ensemble ML compositon', default="./conf.json")
    parser.add_argument('--port', help='default service port', default=5002)
    args = parser.parse_args()

    
    # Serving port
    port = int(args.port)

    # Load configuration file
    config_file = args.conf
    configuration = qoa_utils.load_config(config_file)


    # Load Rest service
    inferenceService = YoloRestService(configuration)
    inferenceService.add_resource(MLInferenceObject, '/inference')
    inferenceService.run(port=port)