from ..external.yolo.model_loader import YoloInference
from .rest_service import RoheRestService


class YoloRestService(RoheRestService):
    def __init__(self, config={}) -> None:
        super().__init__(config)
        self.models = []
        if "composition" in self.config:
            for instance in self.config["composition"]:
                if instance["model"] == "Yolov5":
                    model = YoloInference(self.config, 5, param=instance["parameter"])
                    self.models.append(model)
                if instance["model"] == "Yolov8":
                    model = YoloInference(self.config, 8, param=instance["parameter"])
                    self.models.append(model)
                print("Adding instance: ", instance)
        self.config["models"] = self.models
