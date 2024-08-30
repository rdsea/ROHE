import numpy as np
import torch
from ultralytics.utils.plotting import Annotator

from .prediction_processing import prediction_processing


class Yolo5:
    def __init__(self, checkpoint: str):
        self.checkpoint = checkpoint
        self.model = torch.hub.load("ultralytics/yolov5", checkpoint)

    def convert_results(self, results, annotator):
        # Cast to pandas DataFrame
        pre_pd = results.pandas().xyxy[0]
        # Label object and annotate
        result, annotate = prediction_processing(pre_pd, annotator)
        return {self.checkpoint: result}, annotate

    def yolov_inference(self, image):
        # Images
        annotator = Annotator(np.asarray(image), line_width=1)
        # Inference
        results = self.model(image)
        return self.convert_results(results, annotator)
