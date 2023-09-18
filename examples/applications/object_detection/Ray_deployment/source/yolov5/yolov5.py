import torch, argparse, json, random
from PIL import Image
import cv2,os
import pandas as pd
import numpy as np
from ultralytics.yolo.utils.plotting import Annotator, colors

def not_approximate(a,b):
    if abs(a-b)< 10:
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

class Yolo5(object):
    def __init__(self,param=None):
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.param = param if param is not None else "yolov5s"
        self.model = torch.hub.load(self.path+'/yolov5/', 'custom', source='local', path = self.path+"/model/"+self.param+".pt")

    def convert_results(self, results, annotator):
        # Cast to pandas DataFrame
        pre_pd = results.pandas().xyxy[0]
        # Label object and annotate
        for index, row in pre_pd.iterrows():
            xyxy = row.values.flatten().tolist()[:-2]
            c = int(row["class"])
            label = row["name"] + ":" + str(row["confidence"])
            annotator.box_label(xyxy, label, color=colors(c, True))

        # Conver prediction to dictionary to store in DB
        pre_dict = pre_pd.to_dict("index")
        prediction = []
        key_list = list(pre_dict.keys())
        val_list = list(pre_dict.values())
        object_count = 0
        while key_list:
            pre_obj = [val_list[0]]
            box1 = extract_dict(val_list[0],["xmin", "ymin", "xmax", "ymax"])
            for i in range(1,len(key_list)):
                box2 = extract_dict(val_list[i],["xmin", "ymin", "xmax", "ymax"])
                if compare_box(box1,box2):
                    pre_obj.append(val_list[i])
                    pre_dict.pop(key_list[i])
            detect_obj = {f"object_{object_count}":pre_obj}
            pre_dict.pop(key_list[0])
            key_list = list(pre_dict.keys())
            val_list = list(pre_dict.values())
            object_count += 1
            prediction.append(detect_obj)
        return {self.param:prediction}, annotator.result()


    def yolov_inference(self, image):
        # Images
        annotator = Annotator(np.asarray(image), line_width=1)
        # Inference
        results = self.model(image)
        return self.convert_results(results, annotator)


if __name__ == "__main__":
    args = argparse.ArgumentParser(description="Testing of api-args models.")
    args.add_argument("--conf", type=str, required=True,
                      help="configuration file")
    ag = args.parse_args()
    with open(ag.conf) as config_file:
        config = config_file.read()
    configuration = json.loads(config)
    path = configuration["path"]
    col = ["target","model", "img","img_height", "img_width", "img_channels", "accuracy", "confidence", "obj_height", "obj_width", "obj_height_p", "obj_width_p", "xmin", "xmax", "ymin", "ymax"]
    df = pd.DataFrame(columns=col)
    df.to_csv(configuration["output"])
    for target in configuration["target"]:
        try:
            for model_name in configuration["model_name"]:
                model = Yolo5(model_name)
                print(model_name)
                folder = path+target+"/"
                file_list = os.listdir(folder)
                for file_name in file_list:
                    img = cv2.imread(folder+file_name)
                    prediction, pre_img = model.yolov5_inference(img)
                    object_list = prediction[model_name]
                    dimensions = img.shape
                    img_height = dimensions[0]
                    img_width = img.shape[1]
                    img_channels = img.shape[2]
                    accuracy = 0
                    confidence = 0
                    obj_height = 0
                    obj_width = 0
                    obj_height_p = 100*obj_height/img_height
                    obj_width_p = 100*obj_width/img_width
                    xmin = 0
                    xmax = 0
                    ymin = 0
                    ymax = 0
                    for obj in object_list:
                        for key in obj:
                            for result in obj[key]:
                                if result["name"] == target:
                                    accuracy = 1
                                    confidence = result["confidence"]
                                    obj_height = result["ymax"]-result["ymin"]
                                    obj_width = result["xmax"]-result["xmin"]
                                    obj_height_p = 100*obj_height/img_height
                                    obj_width_p = 100*obj_width/img_width
                                    xmin = result["xmin"]
                                    xmax = result["xmax"]
                                    ymin = result["ymin"]
                                    ymax = result["ymax"]
                                    data = [[target, model_name, file_name, img_height, img_width, img_channels, accuracy, confidence, obj_height, obj_width, 
                                                            obj_height_p, obj_width_p, xmin, xmax, ymin, ymax]]
                                    print(data)
                                    df = pd.DataFrame(data,columns=col)
                                    df.to_csv(configuration["output"], mode='a', header=False)
                    if(accuracy == 0):
                        df = pd.DataFrame([[target, model_name, file_name, img_height, img_width, img_channels, accuracy, confidence, obj_height, obj_width, 
                                                obj_height_p, obj_width_p, xmin, xmax, ymin, ymax]],
                                                columns=col)
                        df.to_csv(configuration["output"], mode='a', header=False)
        except Exception as e:
            print("[ERROR] {}".format(e))

    # cv2.imshow("lable",pre_img)
    # cv2.waitKey(0)