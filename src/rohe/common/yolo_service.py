from ..external.yolo.model_loader import YoloInference
from .rest_service import RoheRestService


class YoloRestService(RoheRestService):
    def __init__(self, config=None) -> None:
        if config is None:
            config = {}
        super().__init__(config)
        self.models = []
        if "composition" in self.config:
            for instance in self.config["composition"]:
                model = YoloInference(
                    self.config, instance["model"], param=instance["parameter"]
                )
                self.models.append(model)
                print("Adding instance: ", instance)
        self.config["models"] = self.models
