import copy
from math import log

import pandas as pd

DEFAULT_ZERO_ERROR_EVA = float("1e-20")


def map_to_log_scale(value, min_value, max_value, logbase):
    # Calculate the logarithmic scale
    min_value = float(min_value)
    max_value = float(max_value)

    if min_value == 0:
        min_value = DEFAULT_ZERO_ERROR_EVA
    if max_value == 0:
        max_value = DEFAULT_ZERO_ERROR_EVA
    if value <= 0:
        value = min_value

    if value < min_value:
        min_value = value
    if value > max_value:
        max_value = value
    log_min = log(min_value, logbase)
    log_max = log(max_value, logbase)

    # Map the value to the logarithmic scale
    # print(value, max_value, min_value)
    log_value = log(value, logbase)

    # Map the logarithmic value to the range [0, 1]
    mapped_value = (log_value - log_min) / (log_max - log_min)

    return mapped_value


def map_to_linear_scale(value, min_value, max_value):
    # Map the linear value to the range [0, 1]
    mapped_value = (value - min_value) / (max_value - min_value)

    return mapped_value


def calculate_statistic(column, statistic):
    if statistic == "max":
        return column.max()
    elif statistic == "min":
        return column.min()
    elif statistic == "sum":
        return column.sum()
    elif statistic in ("avg", "mean"):
        return column.mean()
    elif statistic == "prod":
        return column.prod()
    elif statistic == "rprod":
        new_col = 1 - column
        return 1 - new_col.prod()
    else:
        raise ValueError(
            "Invalid statistic. Valid options are 'prod', 'rprod', sum, 'max', 'min', or 'avg'."
        )


def calculate_scaled_value(value, max_value, min_value, objective, scale, logbase=2):
    if scale == "log":
        scaled_value = map_to_log_scale(value, min_value, max_value, logbase)
    elif scale == "linear":
        scaled_value = map_to_linear_scale(value, min_value, max_value)
    else:
        return None
    if objective == "max":
        return scaled_value
    elif objective == "min":
        return 1 - scaled_value
    return None


def score_estimation(ensemble: list, contract: dict):
    """
    contract example:
    {
        "mlSpecific":{
            "missRateOfClass1and6":{
            "operator": "prod",
            "weight": 1,
            "min_value": 0.00001,
            "max_value": 0.1,
            "objective": "min",
            "scale": "log",
            "logbase": 2
            },
            "missRateOfClass1": {
            "operator": "prod",
            "weight": 1,
            "min_value": 0.00001,
            "max_value": 0.1,
            "objective": "min",
            "scale": "log"
            },
            "generalAccuracy": {
            "operator": "rprod",
            "weight": 1,
            "min_value": 0.6,
            "max_value": 0.99,
            "objective": "max",
            "scale": "log"
            },
            "confidenceOnClass1": {
            "operator": "avg",
            "weight": 1,
            "min_value": 0.5,
            "max_value": 0.95,
            "objective": "max",
            "scale": "log"
            }
        }
    }
    """
    performance_df = pd.DataFrame()
    for ml_service in ensemble:
        row = pd.DataFrame([ml_service.to_dict()])
        performance_df = pd.concat([performance_df, row], ignore_index=True)
    total_score = 0
    metrics = copy.deepcopy(contract["mlSpecific"])
    result = {}
    for metric_key, metric in metrics.items():
        agg_metric = calculate_statistic(performance_df[metric_key], metric["operator"])
        if "logbase" in metric:
            sub_score = calculate_scaled_value(
                agg_metric,
                metric["max_value"],
                metric["min_value"],
                metric["objective"],
                metric["scale"],
                logbase=metric["logbase"],
            )
        else:
            sub_score = calculate_scaled_value(
                agg_metric,
                metric["max_value"],
                metric["min_value"],
                metric["objective"],
                metric["scale"],
            )
        sub_score *= metric["weight"]
        total_score += sub_score
        result[metric_key] = agg_metric
        result[metric_key + "_score"] = sub_score
        # print(metric_key,": ",agg_metric, " ; Sub-score: ",sub_score)
    result["total_score"] = total_score
    return result
