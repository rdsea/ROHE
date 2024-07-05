import math
from itertools import combinations

import pandas as pd

from ...common import rohe_utils
from ...variable import ROHE_PATH
from . import objective

TEMP_PATH = ROHE_PATH + "/temp/nii/ensembleSelection/"


def generate_possible_deployment(model_list, infrastructure_list):
    deployments = []
    deployment_array = [0] * len(model_list)
    deployment_array[0] -= 1
    running_flag = True
    while running_flag:
        # update deployment array
        pointer = 0
        while True:
            if pointer >= len(model_list):
                break
            deployment_array[pointer] += 1
            if deployment_array[pointer] >= len(infrastructure_list):
                deployment_array[pointer] = 0
                pointer += 1
            else:
                break
        if pointer >= len(model_list):
            break

        # add new deployment
        deployment = []
        for i in range(len(model_list)):
            deployment.append(
                {
                    "model": model_list[i],
                    "infrastructure": infrastructure_list[deployment_array[i]],
                }
            )
        deployments.append(deployment)
    return deployments


def scale_reduction(
    model_list: list,
    infrastructure_list: list,
    ml_performance_list: list,
    objective_func_name: str,
    contract: dict,
    to_df: bool = False,
):
    ensemble_constraint = contract["ensemble"]
    max_ensemble_element = ensemble_constraint["max"]
    min_ensemble_element = ensemble_constraint["min"]
    service_constraint = contract["service"]
    throughput_requirement = service_constraint["throughput"]
    for ml_service in ml_performance_list:
        min_throughput = ml_service.metrics["min_throughput"]
        ml_service.scale = math.ceil(throughput_requirement / min_throughput)
        ml_service.metrics["cost"] *= ml_service.scale

    data_df = pd.DataFrame()
    objective_function = rohe_utils.get_function_from_module(
        objective, objective_func_name
    )

    for ensemble_num in range(min_ensemble_element, max_ensemble_element + 1):
        for ensemble in combinations(model_list, ensemble_num):
            possible_deployment = list(
                generate_possible_deployment(list(ensemble), infrastructure_list)
            )
            for deployment in possible_deployment:
                row_dict = {"ensemble": deployment}
                ensemble_service = []
                for service in deployment:
                    selected_service = None
                    for ml_service in ml_performance_list:
                        if (
                            ml_service.model == service["model"]
                            and ml_service.infrastructure == service["infrastructure"]
                        ):
                            selected_service = ml_service
                            break
                    if selected_service is not None:
                        ensemble_service.append(selected_service)

                row_dict.update(objective_function(ensemble_service, contract))
                new_row_df = pd.DataFrame([row_dict])
                data_df = pd.concat([data_df, new_row_df], ignore_index=True)

    if to_df:
        file_name = ""
        for key, metric in contract["mlSpecific"].items():
            file_name += str(key)
            file_name += "{}_".format(str(metric["weight"]))
        data_df.to_csv(TEMP_PATH + f"{file_name}.csv")
    highest_row = data_df.loc[data_df["total_score"].idxmax()]
    return highest_row.to_dict()
