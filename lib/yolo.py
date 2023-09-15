from lib.yolov8.yolov8 import Yolo8
from lib.yolov5.yolov5 import Yolo5
from lib.restService import RoheRestService

class YoloInference:
    def __init__(self, param, version):
        self.param = param
        if version == 5:
            self.model = Yolo5(param)
        elif version == 8:
            self.model = Yolo8(param)

    def predict(self, image, report_list=[]):
        prediction, pre_img = self.model.yolov_inference(image)
        return {"prediction": prediction, "image": pre_img}, {}
    

class YoloRestService(RoheRestService): 
    def __init__(self, config={}) -> None:
        super().__init__(config)
        self.models = []
        if "composition" in self.config:
            for instance in self.config["composition"]:
                if instance["model"] == "Yolov5":
                    model = YoloInference(instance["parameter"], 5)
                    self.models.append(model)
                if instance["model"] == "Yolov8":
                    model = YoloInference(instance["parameter"], 8) 
                    self.models.append(model)
                print("Adding instance: ", instance)
        self.config["models"] = self.models