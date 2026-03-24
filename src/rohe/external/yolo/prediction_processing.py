from ultralytics.utils.plotting import colors

NOT_APPROXIMATE_THRESHOLD = 10


def not_approximate(a, b):
    if abs(a - b) < NOT_APPROXIMATE_THRESHOLD:
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
    for _index, row in prediction.iterrows():
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
