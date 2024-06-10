import pandas as pd

class_label_dict = {
    0: "bicycle",
    1: "bus",
    2: "car",
    3: "motorcycle",
    4: "other person",
    5: "other vehicle",
    6: "pedestrian",
    7: "rider",
    8: "traffic light",
    9: "traffic sign",
    10: "trailer",
    11: "train",
    12: "truck",
}


def get_risk_levels_info(dataframe: pd.DataFrame, class_label_dict: dict) -> dict:
    dataframe = dataframe.copy(deep=True)

    def map_label(class_object):
        return class_label_dict.get(class_object, "Unknown")

    def misclassification_num(df, true_label, false_label=None):
        subset = df[df["label"] == true_label]
        if false_label:
            misclassified = subset[subset["predict_label"] == false_label]
        else:
            misclassified = subset[subset["predict_label"] != true_label]
        if len(subset) == 0:
            return 0
        return len(misclassified)

    def calculate_risk_level(df):
        df["label"] = df["class_object"].map(map_label)
        df["predict_label"] = df["predict_object"].map(map_label)

        # Risk Level 1
        miss_ped_num = misclassification_num(df, "pedestrian")
        miss_car_as_rider_num = misclassification_num(df, "car", "rider")
        total_ped = len(df[df["label"] == "pedestrian"])
        total_car = len(df[df["label"] == "car"])

        if total_ped + total_car == 0:
            risk_level_1 = 0
        else:
            risk_level_1 = (miss_ped_num + miss_car_as_rider_num) / (
                total_ped + total_car
            )

        print(f"risk level 1: {risk_level_1}")
        print(
            f"This is total missclassify number for risk level 1: {miss_ped_num + miss_car_as_rider_num} and total object is : {total_ped + total_car}"
        )

        # Risk Level 2
        miss_rider_num = misclassification_num(df, "rider")
        miss_car_as_truck_num = misclassification_num(df, "car", "truck")
        miss_bicycle_num = misclassification_num(df, "bicycle")
        total_rider = len(df[df["label"] == "rider"])
        total_truck = len(df[df["label"] == "truck"])
        total_bicycle = len(df[df["label"] == "bicycle"])
        if total_rider + total_truck + total_bicycle == 0:
            risk_level_2 = 0
        else:
            risk_level_2 = (
                miss_rider_num + miss_car_as_truck_num + miss_bicycle_num
            ) / (total_rider + total_truck + total_bicycle)

        print(f"risk level 2: {risk_level_2}")

        print(
            f"This is total missclassify number for risk level 2: {miss_rider_num + miss_car_as_truck_num + miss_bicycle_num} and total object is {total_rider + total_truck + total_bicycle}"
        )

        # Risk Level 3
        miss_ped_num_rider = misclassification_num(df, "pedestrian", "rider")
        miss_rider_as_ped_num = misclassification_num(df, "rider", "pedestrian")
        miss_motor_as_ped_num = misclassification_num(df, "motorcycle", "pedestrian")
        total_motorcycle = len(df[df["label"] == "motorcycle"])
        if total_ped + total_rider + total_motorcycle == 0:
            risk_level_3 = 0
        else:
            risk_level_3 = (
                miss_ped_num_rider + miss_rider_as_ped_num + miss_motor_as_ped_num
            ) / (total_ped + total_rider + total_motorcycle)
        print(f"risk level 3: {risk_level_3}")

        print(
            f"This is total missclassify number for risk level 3: {miss_ped_num_rider + miss_rider_as_ped_num + miss_motor_as_ped_num} and total object is {total_ped + total_rider + total_motorcycle}"
        )

        return {
            "risk_level_1": risk_level_1 * 100,
            "risk_level_2": risk_level_2 * 100,
            "risk_level_3": risk_level_3 * 100,
        }

    report = calculate_risk_level(dataframe)

    return report


def get_resource(hostname: str):
    if not hostname:
        import socket

        hostname = socket.gethostname()
    return hostname
