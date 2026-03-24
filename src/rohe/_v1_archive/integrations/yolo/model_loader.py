from . import yolov5, yolov8


class YoloInference:
    def __init__(self, version: str, checkpoint: str):
        if version == "Yolov5":
            self.model = yolov5.Yolo5(checkpoint)
        elif version == "Yolov8":
            self.model = yolov8.Yolo8(checkpoint)
        else:
            raise RuntimeError(f"Unrecognize {version}")

    def predict(self, image, report_list=None):
        if report_list is None:
            report_list = []
        prediction, pre_img = self.model.yolov_inference(image)
        return {"prediction": prediction, "image": pre_img}, {}
