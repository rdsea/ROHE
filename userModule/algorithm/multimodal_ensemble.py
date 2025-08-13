import os
import sys
import logging
import time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)
from rohe.orchestration.multimodal_abstration import InferenceTask, InferenceResult, CommonMetric, InferenceServiceInstance, Explainability
import traceback
import userModule.plugin as plugin


def get_function_from_plugin(app_name: str, plugin_name: str):
    try:
        app_module = getattr(plugin, app_name, None)
        function = getattr(app_module, plugin_name, None)
        return function if callable(function) else None
    except Exception as e:
        logging.error(f"Error getting function {plugin_name} from plugin {app_name}: {e}")
        return None

def enhance_confidence(app_name: str, plugin_name: str, task: InferenceTask, intermediate_result: InferenceResult, top_k: int = 1):
    try:
        task.selected_instances = []
        used_services = []
        top_k_function = get_function_from_plugin(app_name=app_name, plugin_name=plugin_name)
        top_k_classes = top_k_function(intermediate_result.data, top_k=top_k)
        if top_k > len(top_k_classes):
            logging.debug(f"Requested top_k {top_k} is greater than available classes {len(top_k_classes)} selecting k classes by default.")
        inference_instances = task.inference_instances
        inference_services = task.inference_services
        for i in range(top_k):
            selected_service_i = None
            selected_service_ex_i = None
            best_accuracy = 0
            best_accuracy_ex = 0
            if i >= len(top_k_classes):
                for key, value in inference_services.items():
                    inference_performance = value.inference_performance
                    overall_performance = inference_performance.overall_performance
                    for metric in overall_performance:
                        metric_name = metric.metric_name
                        metric_value = metric.value
                        if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy and key not in used_services:
                            best_accuracy = metric_value
                            selected_service_i = key
                if i == 0 and task.explainability:
                    for key, value in task.inference_services_ex.items():
                        inference_performance = value.inference_performance
                        overall_performance = inference_performance.overall_performance
                        for metric in overall_performance:
                            metric_name = metric.metric_name
                            metric_value = metric.value
                            if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy_ex and key not in used_services:
                                best_accuracy_ex = metric_value
                                selected_service_ex_i = key
            else:
                top_i_class = top_k_classes[i]
                for key, value in inference_services.items():
                    inference_performance = value.inference_performance
                    class_specific_performance = inference_performance.class_specific_performance
                    for class_specific_metric in class_specific_performance:
                        class_name = class_specific_metric.class_name
                        if class_name == top_i_class:
                            i_performance = class_specific_metric.performance
                            for metric in i_performance:
                                metric_name = metric.metric_name
                                metric_value = metric.value
                                if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy and key not in used_services:
                                    best_accuracy = metric_value
                                    selected_service_i = key
                if i == 0 and task.explainability:
                    for key, value in task.inference_services_ex.items():
                        inference_performance = value.inference_performance
                        class_specific_performance = inference_performance.class_specific_performance
                        for class_specific_metric in class_specific_performance:
                            class_name = class_specific_metric.class_name
                            if class_name == top_i_class:
                                i_performance = class_specific_metric.performance
                                for metric in i_performance:
                                    metric_name = metric.metric_name
                                    metric_value = metric.value
                                    if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy_ex and key not in used_services:
                                        best_accuracy_ex = metric_value
                                        selected_service_ex_i = key
            logging.debug(f"Selected service {selected_service_i} with accuracy {best_accuracy} for task {task.task_id} at iteration {i}.")
            if selected_service_i:
                used_services.append(selected_service_i)
                instance_list_i = inference_services.get(selected_service_i).instance_list
                best_response_time_i = float('-inf')
                selected_instance_i = None
                for instance_key_j in instance_list_i:
                    if instance_key_j in list(inference_instances.keys()):
                        instance_j = inference_instances[instance_key_j]
                        runtime_performance_j = instance_j.runtime_performance
                        for metric_k in runtime_performance_j:
                            if metric_k.metric_name == CommonMetric.RESPONSE_TIME.value and metric_k.condition == Explainability.DISABLED.value:
                                response_time_k = metric_k.value
                                if response_time_k > best_response_time_i:
                                    best_response_time_i = response_time_k
                                    selected_instance_i = instance_j
                if selected_instance_i:
                    task.selected_instances.append(selected_instance_i)
                    logging.debug(f"Selected instance {selected_instance_i.instance_id} for service {selected_service_i} in task {task.task_id}.")
                else:
                    logging.warning(f"No suitable instance found for service {selected_service_i} in task {task.task_id}.")
            else:
                logging.warning(f"No suitable service found for task {task.task_id} at iteration {i}.")
            if i == 0 and task.explainability and selected_service_ex_i:
                used_services.append(selected_service_ex_i)
                instance_list_ex_i = task.inference_services_ex.get(selected_service_ex_i).instance_list
                best_response_time_ex_i = float('-inf')
                selected_instance_ex_i = None
                for instance_key_j in instance_list_ex_i:
                    if instance_key_j in list(inference_instances.keys()):
                        instance_j = inference_instances[instance_key_j]
                        runtime_performance_j = instance_j.runtime_performance
                        for metric_k in runtime_performance_j:
                            if metric_k.metric_name == CommonMetric.RESPONSE_TIME.value and metric_k.condition == Explainability.ENABLED.value:
                                response_time_k = metric_k.value
                                if response_time_k > best_response_time_ex_i:
                                    best_response_time_ex_i = response_time_k
                                    selected_instance_ex_i = instance_j
                if selected_instance_ex_i:
                    task.selected_instances_ex.append(selected_instance_ex_i)
                    logging.debug(f"Selected explainable instance {selected_instance_ex_i.instance_id} for service {selected_service_ex_i} in task {task.task_id}.")
                else:
                    logging.warning(f"No suitable explainable instance found for service {selected_service_ex_i} in task {task.task_id}.")
            
        logging.debug(f"Task {task.task_id} selected {len(task.selected_instances)} instances out of requested top_k {top_k}.")
        if len(task.selected_instances) < top_k:
            logging.warning(f"Not enough instances selected for task {task.task_id}. Selected {len(task.selected_instances)} out of {top_k}.")
    except Exception as e:
        logging.error(f"Error in enhancing confidence for task {task.task_id}: {e}")
        logging.error(traceback.format_exc())
        
        
def enhance_generalization(task: InferenceTask, intermediate_result: InferenceResult, worst_k: int = 1):
    try:
        task.selected_instances = []
        used_services = []
        worst_k_classes = intermediate_result.get_worst_k_predictions(worst_k=worst_k)
        if worst_k > len(worst_k_classes):
            logging.debug(f"Requested worst_k {worst_k} is greater than available classes {len(worst_k_classes)} selecting k classes by default.")
        inference_instances = task.inference_instances
        inference_services = task.inference_services
        for i in range(worst_k):
            selected_service_i = None
            selected_service_ex_i = None
            best_accuracy = 0
            best_accuracy_ex = 0
            if i >= len(worst_k_classes):
                for key, value in inference_services.items():
                    inference_performance = value.inference_performance
                    overall_performance = inference_performance.overall_performance
                    for metric in overall_performance:
                        metric_name = metric.metric_name
                        metric_value = metric.value
                        if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy and key not in used_services:
                            best_accuracy = metric_value
                            selected_service_i = key
                if i == 0 and task.explainability:
                    for key, value in task.inference_services_ex.items():
                        inference_performance = value.inference_performance
                        overall_performance = inference_performance.overall_performance
                        for metric in overall_performance:
                            metric_name = metric.metric_name
                            metric_value = metric.value
                            if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy_ex and key not in used_services:
                                best_accuracy_ex = metric_value
                                selected_service_ex_i = key
            else:
                worst_i_class = worst_k_classes[i]
                for key, value in inference_services.items():
                    inference_performance = value.inference_performance
                    class_specific_performance = inference_performance.class_specific_performance
                    for class_specific_metric in class_specific_performance:
                        class_name = class_specific_metric.class_name
                        if class_name == worst_i_class:
                            i_performance = class_specific_metric.performance
                            for metric in i_performance:
                                metric_name = metric.metric_name
                                metric_value = metric.value
                                if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy and key not in used_services:
                                    best_accuracy = metric_value
                                    selected_service_i = key
                if i == 0 and task.explainability:
                    for key, value in task.inference_services_ex.items():
                        inference_performance = value.inference_performance
                        class_specific_performance = inference_performance.class_specific_performance
                        for class_specific_metric in class_specific_performance:
                            class_name = class_specific_metric.class_name
                            if class_name == worst_i_class:
                                i_performance = class_specific_metric.performance
                                for metric in i_performance:
                                    metric_name = metric.metric_name
                                    metric_value = metric.value
                                    if metric_name == CommonMetric.ACCURACY.value and metric_value > best_accuracy_ex and key not in used_services:
                                        best_accuracy_ex = metric_value
                                        selected_service_ex_i = key
            logging.debug(f"Selected service {selected_service_i} with accuracy {best_accuracy} for task {task.task_id} at iteration {i}.")
            if selected_service_i:
                used_services.append(selected_service_i)
                instance_list_i = inference_services.get(selected_service_i).instance_list
                best_response_time_i = float('-inf')
                selected_instance_i = None
                for instance_key_j in instance_list_i:
                    if instance_key_j in list(inference_instances.keys()):
                        instance_j = inference_instances[instance_key_j]
                        runtime_performance_j = instance_j.runtime_performance
                        for metric_k in runtime_performance_j:
                            if metric_k.metric_name == CommonMetric.RESPONSE_TIME.value and metric_k.condition == Explainability.DISABLED.value:
                                response_time_k = metric_k.value
                                if response_time_k > best_response_time_i:
                                    best_response_time_i = response_time_k
                                    selected_instance_i = instance_j
                if selected_instance_i:
                    task.selected_instances.append(selected_instance_i)
                    logging.debug(f"Selected instance {selected_instance_i.instance_id} for service {selected_service_i} in task {task.task_id}.")
                else:
                    logging.warning(f"No suitable instance found for service {selected_service_i} in task {task.task_id}.")
            else:
                logging.warning(f"No suitable service found for task {task.task_id} at iteration {i}.")
            if i == 0 and task.explainability and selected_service_ex_i:
                used_services.append(selected_service_ex_i)
                instance_list_ex_i = task.inference_services_ex.get(selected_service_ex_i).instance_list
                best_response_time_ex_i = float('-inf')
                selected_instance_ex_i = None
                for instance_key_j in instance_list_ex_i:
                    if instance_key_j in list(inference_instances.keys()):
                        instance_j = inference_instances[instance_key_j]
                        runtime_performance_j = instance_j.runtime_performance
                        for metric_k in runtime_performance_j:
                            if metric_k.metric_name == CommonMetric.RESPONSE_TIME.value and metric_k.condition == Explainability.ENABLED.value:
                                response_time_k = metric_k.value
                                if response_time_k > best_response_time_ex_i:
                                    best_response_time_ex_i = response_time_k
                                    selected_instance_ex_i = instance_j
                if selected_instance_ex_i:
                    task.selected_instances_ex.append(selected_instance_ex_i)
                    logging.debug(f"Selected explainable instance {selected_instance_ex_i.instance_id} for service {selected_service_ex_i} in task {task.task_id}.")
                else:
                    logging.warning(f"No suitable explainable instance found for service {selected_service_ex_i} in task {task.task_id}.")

        logging.debug(f"Task {task.task_id} selected {len(task.selected_instances)} instances out of requested worst_k {worst_k}.")
        if len(task.selected_instances) < worst_k:
            logging.warning(f"Not enough instances selected for task {task.task_id}. Selected {len(task.selected_instances)} out of {worst_k}.")
    except Exception as e:
        logging.error(f"Error in enhancing confidence for task {task.task_id}: {e}")
        logging.error(traceback.format_exc())