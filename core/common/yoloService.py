from core.external.yolo.modelLoader import YoloInference
from core.common.restService import RoheRestService
    

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