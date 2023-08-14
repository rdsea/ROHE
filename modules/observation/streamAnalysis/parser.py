import logging, traceback,sys
import pandas as pd
from sklearn.ensemble import IsolationForest
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)
model=IsolationForest(n_estimators=50, max_samples='auto', contamination=float(0.1),max_features=1.0)


def cpustatParser(buff, parser_conf):
    try:
        # Get window data from buffer
        data = buff.get()
        # Create data frame to store result
        proc_df = pd.DataFrame()

        # parse each item in data
        for item in data:
            # Get cpu stats
            if "proc_cpu_stats" in item:
                key = list(item["proc_cpu_stats"].keys())[0]
                cpustat = [item["proc_cpu_stats"][key]["user"]]
            # Get metadate for later analyses
            if "metadata" in item:
                client_id = [item["metadata"]["client_id"]]
                instance_name = [item["metadata"]["instance_name"]]
                instances_id = [item["metadata"]["instances_id"]]
                timestamp = [item["metadata"]["timestamp"]]
                stage_id = [item["metadata"]["stage_id"]]
                application = [item["metadata"]["application"]]
            # Creat new row data
            dfi = pd.DataFrame({"cpustats":cpustat,
                                "client_id":client_id,
                                "instance_name":instance_name,
                                "instances_id":instances_id,
                                "timestamp":timestamp,
                                "stage_id":stage_id,
                                "application":application})
            # concat new row data to result dataframe 
            proc_df = pd.concat([proc_df, dfi], ignore_index=True)
        return proc_df, ["cpustats"]
    except Exception as e:
        logging.error("Error {} while parsing cpustats: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None


def confidenceParser(buff, parser_conf):
    try:
        data = buff.get()
        inf_df = pd.DataFrame()
        for item in data:
            # Get confidence
            if "quality" in item:
                last_inf = item["quality"]["inference"]["last_inference"]
                confidence = item["quality"]["inference"][last_inf]["confidence"]["value"]
            # Get metadate for later analyses
            if "metadata" in item:
                client_id = [item["metadata"]["client_id"]]
                instance_name = [item["metadata"]["instance_name"]]
                instances_id = [item["metadata"]["instances_id"]]
                timestamp = [item["metadata"]["timestamp"]]
                stage_id = [item["metadata"]["stage_id"]]
                application = [item["metadata"]["application"]]
            # Creat new row data
            dfi = pd.DataFrame({"confidence":confidence,
                                    "client_id":client_id,
                                    "instance_name":instance_name,
                                    "instances_id":instances_id,
                                    "timestamp":timestamp,
                                    "stage_id":stage_id,
                                    "application":application})
            # concat new row data to result dataframe 
            inf_df = pd.concat([inf_df, dfi], ignore_index=True)
        return inf_df, ["confidence"]
    except Exception as e:
        logging.error("Error {} while parsing confidence: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None
    
def accuracyParser(buff, parser_conf):
    try:
        data = buff.get()
        inf_df = pd.DataFrame()
        for item in data:
            # Get accuracy
            if "quality" in item:
                last_inf = item["quality"]["inference"]["last_inference"]
                accuracy = item["quality"]["inference"][last_inf]["accuracy"]["value"]
            # Get metadate for later analyses
            if "metadata" in item:
                client_id = [item["metadata"]["client_id"]]
                instance_name = [item["metadata"]["instance_name"]]
                instances_id = [item["metadata"]["instances_id"]]
                timestamp = [item["metadata"]["timestamp"]]
                stage_id = [item["metadata"]["stage_id"]]
                application = [item["metadata"]["application"]]
            # Creat new row data
            dfi = pd.DataFrame({"accuracy":accuracy,
                                    "client_id":client_id,
                                    "instance_name":instance_name,
                                    "instances_id":instances_id,
                                    "timestamp":timestamp,
                                    "stage_id":stage_id,
                                    "application":application})
            # concat new row data to result dataframe 
            inf_df = pd.concat([inf_df, dfi], ignore_index=True)
        return inf_df, ["accuracy"]
    except Exception as e:
        logging.error("Error {} while parsing accuracy: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None
    
def get_inference_metric(report, metric_name):
    # get a inference metric via metric name and inference report
    # return a dictionary that can converted to DataFrame
    last_inf = report["last_inference"]
    return {metric_name: [report[last_inf][metric_name]["value"]]}

def get_data_quality_metric(report, metric_config):
    # get a data quality metric via metric name and data quality report
    # return a dictionary that can converted to DataFrame
    metric_name = metric_config["name"]
    stage = metric_config["stage"]
    aggregate_method = metric_config["aggregate"]

    # Aggregate value among value from instances of the same metric
    if aggregate_method == "mean":
        sum_value = 0
        for instance in report[stage][metric_name]:
            sum_value += report[stage][metric_name][instance]
        mean_value = sum_value/len(list(report[stage][metric_name].keys()))
        return {metric_name : [mean_value]}
    if aggregate_method == "max":
        max_value = float('-inf')
        for instance in report[stage][metric_name]:
            if report[stage][metric_name][instance] > max_value:
                max_value = report[stage][metric_name][instance]
        return {metric_name : [max_value]}
    if aggregate_method == "min":
        min_value = float('inf')
        for instance in report[stage][metric_name]:
            if report[stage][metric_name][instance] < max_value:
                min_value = report[stage][metric_name][instance]
        return {metric_name : [min_value]}
    else:
        logging.warning("Return empty data quality metric in get_data_quality_metric: ")
        return {}


def replace_feature(feature, metric_name, replacements):
    # Update feature name if metric names are updated
    new_feature = []
    for item in feature:
        new_item = []
        for metric in item:
            if metric != metric_name:
                new_item.append(metric_name)
            else:
                new_item.extend(replacements)
    new_feature.append(new_item)
    return new_feature

def objectDetectionParser(buff, parser_conf):
    try:
        data = buff.get()
        inf_df = pd.DataFrame()
        metric_list = parser_conf["metric"]
        feature_list = parser_conf["feature"]
        for item in data:
            # Get quality report 
            if "quality" in item:
                quality_report = item["quality"]
                # Init an empty dictionary to store metrics
                metric_cols = {} 
                if ("inference" in metric_list) and ("inference" in quality_report):
                    # Get inference metrics
                    for inf_metric in metric_list["inference"]:
                        metric_cols.update(get_inference_metric(quality_report["inference"], inf_metric))
                if ("data" in metric_list) and ("data" in quality_report):
                    # Get data quality metrics
                    for data_metric in metric_list["data"]:
                        metric_cols.update(get_data_quality_metric(quality_report["data"], data_metric))




            # Get metadate for later analyses
            if "metadata" in item:
                client_id = [item["metadata"]["client_id"]]
                instance_name = [item["metadata"]["instance_name"]]
                instances_id = [item["metadata"]["instances_id"]]
                timestamp = [item["metadata"]["timestamp"]]
                stage_id = [item["metadata"]["stage_id"]]
                application = [item["metadata"]["application"]]
            # Creat new row data
            row_dict = {"client_id":client_id,
                        "instance_name":instance_name,
                        "instances_id":instances_id,
                        "timestamp":timestamp,
                        "stage_id":stage_id,
                        "application":application}
            row_dict.update(metric_cols)
            dfi = pd.DataFrame(row_dict)
            # concat new row data to result dataframe 
            inf_df = pd.concat([inf_df, dfi], ignore_index=True)
        return inf_df, feature_list
    except Exception as e:
        logging.error("Error {} while parsing data in objectDetectionParser: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None
    