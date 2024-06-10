def not_approximate(a, b):
    if abs(a - b) < 10:
        return False
    else:
        return True


def get_prediction(list_pre, i):
    pre_item = list_pre[i]
    keys = list(pre_item.keys())
    return pre_item[keys[0]]


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


def agg_mean(predict_list):
    merged_dict = predict_list[0]
    for i in range(1, len(predict_list)):
        for key in predict_list[i]:
            if key not in merged_dict:
                merged_dict[key] = predict_list[i][key]
            else:
                merged_dict[key] += predict_list[i][key]
    for key in merged_dict:
        merged_dict[key] /= len(predict_list)
    return merged_dict


def agg_max(predictions):
    pre_list = []
    agg_prediction = []
    object_count = 0
    for key in predictions:
        pre_list += predictions[key]
    while pre_list:
        pre_item = get_prediction(pre_list, 0)
        box1 = extract_dict(pre_item[0], ["xmin", "ymin", "xmax", "ymax"])
        duplicate = []
        for i in range(1, len(pre_list)):
            box2 = extract_dict(
                get_prediction(pre_list, i)[0], ["xmin", "ymin", "xmax", "ymax"]
            )
            if compare_box(box1, box2):
                pre_item += get_prediction(pre_list, i)
                duplicate.append(i)
        for item in duplicate:
            pre_list.pop(item)
        max_item = pre_item[0]
        for item in pre_item:
            if item["confidence"] > max_item["confidence"]:
                max_item = item
        detect_obj = {f"object_{object_count}": max_item}
        pre_list.pop(0)
        object_count += 1
        agg_prediction.append(detect_obj)
    return agg_prediction
