# import qoa4ml.utils as utils
# import sys
# main_path = config_file = utils.get_parent_dir(__file__,1)
# sys.path.append(main_path)
from lib.roheObject import RoheObject

from flask import Flask, jsonify, request
from flask_restful import Resource, Api




class RoheRestObject(Resource, RoheObject):
    def __init__(self) -> None:
        super().__init__()
        
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


class RoheRestService(object): 
    def __init__(self, config) -> None:
        super().__init__()
        self.app = Flask(__name__)
        self.api = Api(self.app)
        self.config = config

    def add_resource(self, object_class, url):
        # Run Service
        self.api.add_resource(object_class, url,resource_class_kwargs=self.config)
    
    def run(self, debug=True, port=5010,host="0.0.0.0"):
        self.app.run(debug=debug, port=port,host=host)