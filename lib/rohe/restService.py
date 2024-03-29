import qoa4ml.qoaUtils as qoaUtils
import sys, json
from flask import Response
main_path = config_file = qoaUtils.get_parent_dir(__file__,2)
sys.path.append(main_path)
from lib.rohe.roheObject import RoheObject

from flask import Flask, jsonify, request
from flask_restful import Resource, Api




class RoheRestObject(Resource, RoheObject):
    def __init__(self, log_level: int = 2) -> None:
        super().__init__(logging_level= log_level)
        
    def get(self):
        # Processing GET request
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})
    
    def post(self):
        # Processing GET request
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})
    
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
    
    
class ImageInferenceObject(RoheRestObject):
    def __init__(self) -> None:
        super().__init__()
    
    def post(self):
        json_data = {}
        try:
            data = {}
            data['image'] = request.files['image'].read()
            if "report" in request.files:
                data['report'] = json.loads(request.files['report'].read())
            json_data = self.imageProcessing(data)
        except Exception as e:
            json_data = '{"error":"some error occurred in Rest processing service"}'
            print(e)
        result = json.dumps(json_data)
        return Response(response=result, status=200)
    
    def imageProcessing(self, image):
        return {}

class RoheRestService(object): 
    def __init__(self, config={}) -> None:
        super().__init__()
        self.app = Flask(__name__)
        self.api = Api(self.app)
        self.config = config

    def add_resource(self, object_class, url):
        # Run Service
        self.api.add_resource(object_class, url,resource_class_kwargs=self.config)
    
    def run(self, debug=True, port=5010,host="0.0.0.0"):
        self.app.run(debug=debug, port=port,host=host,use_reloader=False)
