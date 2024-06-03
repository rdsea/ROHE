import os

import gdown
import git
import numpy as np
import pandas as pd
import torch
import yaml
from ultralytics import YOLO
from ultralytics.yolo.utils.plotting import Annotator, colors


class YoloInference:
    def __init__(self, config, version, param):
        self.param = param
        self.config = config
        if version == 5:
            self.model = Yolo5(config, param)
        elif version == 8:
            self.model = Yolo8(config, param)

    def predict(self, image, report_list=[]):
        prediction, pre_img = self.model.yolov_inference(image)
        return {"prediction": prediction, "image": pre_img}, {}


def not_approximate(a, b):
    if abs(a - b) < 10:
        return False
    else:
        return True


def extract_dict(dict, keys):
    result = {}
    for key in keys:
        result[key] = dict[key]
    return result


def compare_box(box1, box2):
    for key in box1:
        if not_approximate(box1[key], box2[key]):
            return False
    return True


def prediction_processing(prediction, annotator):
    for index, row in prediction.iterrows():
        xyxy = row.values.flatten().tolist()[:-2]
        c = int(row["class"])
        label = row["name"] + ":" + str(row["confidence"])
        annotator.box_label(xyxy, label, color=colors(c, True))

    # Conver prediction to dictionary to store in DB

    pre_dict = prediction.to_dict("index")
    prediction = []
    key_list = list(pre_dict.keys())
    val_list = list(pre_dict.values())
    object_count = 0
    while key_list:
        pre_obj = [val_list[0]]
        box1 = extract_dict(val_list[0], ["xmin", "ymin", "xmax", "ymax"])
        for i in range(1, len(key_list)):
            box2 = extract_dict(val_list[i], ["xmin", "ymin", "xmax", "ymax"])
            if compare_box(box1, box2):
                pre_obj.append(val_list[i])
                pre_dict.pop(key_list[i])
        detect_obj = {f"object_{object_count}": pre_obj}
        pre_dict.pop(key_list[0])
        key_list = list(pre_dict.keys())
        val_list = list(pre_dict.values())
        object_count += 1
        prediction.append(detect_obj)
    return prediction, annotator.result()


class Yolo5(object):
    def __init__(self, config, param=None):
        self.lib_path = config["artifact"]["lib"]
        print(self.lib_path)
        self.conf = config
        if not os.path.exists(self.lib_path):
            print("folder not exist -> creating new folder")
            os.makedirs(self.lib_path)
            # clone lib
            repo = git.Repo.clone_from(
                self.conf["repo"]["url"], self.lib_path, no_checkout=True
            )
            repo.git.checkout(self.conf["repo"]["commit_id"])

        self.artifact_path = config["artifact"]["dir"]
        if not os.path.exists(self.artifact_path + "yolo/"):
            file_url = self.conf["artifact"]["url"]
            gdown.cached_download(
                file_url, self.artifact_path + "yolo.zip", postprocess=gdown.extractall
            )
        self.param = param if param is not None else "yolov5s"
        self.model = torch.hub.load(
            self.lib_path,
            "custom",
            source="local",
            path=self.artifact_path + "yolo/" + self.param + ".pt",
        )

    def convert_results(self, results, annotator):
        # Cast to pandas DataFrame
        pre_pd = results.pandas().xyxy[0]
        # Label object and annotate
        result, annotate = prediction_processing(pre_pd, annotator)
        return {self.param: result}, annotate

    def yolov_inference(self, image):
        # Images
        annotator = Annotator(np.asarray(image), line_width=1)
        # Inference
        results = self.model(image)
        return self.convert_results(results, annotator)


class Yolo8(object):
    def __init__(self, config, param=None):
        self.artifact_path = config["artifact"]["dir"]
        self.conf = config
        if not os.path.exists(self.artifact_path):
            file_url = self.conf["artifact"]["url"]
            gdown.cached_download(
                file_url, self.artifact_path + "yolo.zip", postprocess=gdown.extractall
            )
        class_conf = self.artifact_path + "yolo/class.yml"
        with open(class_conf, "r") as f:
            self.names = yaml.safe_load(f)
        self.param = param if param is not None else "yolov8s"
        self.model = YOLO(self.artifact_path + "yolo/" + self.param + ".pt")

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
            prediction["name"] = prediction["class"].apply(
                lambda x: self.names["names"][x]
            )
            # Label object and annotate
            result, annotate = prediction_processing(prediction, annotator)
            return {self.param: result}, annotate
        return None

    def yolov_inference(self, image):
        annotator = Annotator(image, line_width=1)
        # Inference
        results = self.model.predict(image, stream=True)
        return self.convert_results(results, annotator)
