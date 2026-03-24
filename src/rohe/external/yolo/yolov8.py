import os

import pandas as pd
import yaml
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator

from .prediction_processing import prediction_processing

current_dir = os.path.dirname(os.path.realpath(__file__))


class Yolo8:
    def __init__(self, checkpoint: str):
        with open(f"{current_dir}/class.yml") as f:
            self.names = yaml.safe_load(f)
        self.checkpoint = checkpoint
        self.model = YOLO(self.checkpoint)

    def convert_results(self, results, annotator):
        for result in results:
            # convert detection to numpy array
            numpy_result = result.boxes.numpy().data
            # Cast to pandas DataFrame
            prediction = pd.DataFrame(
                numpy_result,
                columns=["xmin", "ymin", "xmax", "ymax", "confidence", "class"],
            )
            # Map to class names
            prediction["name"] = prediction["class"].apply(lambda x: self.names[x])
            # Label object and annotate
            return_result, annotate = prediction_processing(prediction, annotator)
            return {self.checkpoint: return_result}, annotate
        return None

    def yolov_inference(self, image):
        annotator = Annotator(image, line_width=1)
        # Inference
        results = self.model.predict(image, stream=True)
        return self.convert_results(results, annotator)
