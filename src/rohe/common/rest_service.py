import json

from flask import Flask, Response, request
from flask_restful import Api, Resource


class RoheRestResource(Resource):
    def __init__(self) -> None:
        pass

    # def get(self):
    #     # Processing GET request
    #     args = request.query_string.decode("utf-8").split("&")
    #     # get param from args here
    #     return jsonify({"status": args})
    #
    # def post(self):
    #     # Processing GET request
    #     args = request.query_string.decode("utf-8").split("&")
    #     # get param from args here
    #     return jsonify({"status": args})
    #
    # def put(self):
    #     # if request.is_json:
    #     #     args = request.get_json(force=True)
    #     # get param from args here
    #     return jsonify({"status": True})
    #
    # def delete(self):
    #     if request.is_json:
    #         args = request.get_json(force=True)
    #     # get param from args here
    #     return jsonify({"status": args})


class ImageInferenceObject(RoheRestResource):
    def __init__(self) -> None:
        super().__init__()

    def post(self):
        json_data = {}
        try:
            data = {}
            data["image"] = request.files["image"].read()
            if "report" in request.files:
                data["report"] = json.loads(request.files["report"].read())
            json_data = self.image_processing(data)
        except Exception as e:
            json_data = '{"error":"some error occurred in Rest processing service"}'
            print(e)
        result = json.dumps(json_data)
        return Response(response=result, status=200)

    def image_processing(self, image):
        return {}


class RoheRestService:
    def __init__(self, config=None) -> None:
        if config is None:
            config = {}
        super().__init__()
        self.app = Flask(__name__)
        self.api = Api(self.app)
        self.config = config

    def add_resource(self, object_class, url, resource_config=None):
        # Run Service
        if resource_config is None:
            self.api.add_resource(object_class, url, resource_class_kwargs=self.config)
        else:
            self.api.add_resource(
                object_class, url, resource_class_kwargs=resource_config
            )

    def run(self, debug=True, port=5010, host="0.0.0.0"):
        self.app.run(debug=debug, port=port, host=host, use_reloader=False)
