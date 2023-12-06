import logging, traceback,sys, copy, os
import pandas as pd
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)


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
                userID = [item["metadata"]["userID"]]
                instanceID = [item["metadata"]["instanceID"]]
                timestamp = [item["metadata"]["timestamp"]]
                stageID = [item["metadata"]["stageID"]]
                appName = [item["metadata"]["appName"]]
                runID = [item["metadata"]["runID"]]
            # Creat new row data
            dfi = pd.DataFrame({"cpustats":cpustat,
                                "userID":userID,
                                "instanceID":instanceID,
                                "runID":runID,
                                "timestamp":timestamp,
                                "stageID":stageID,
                                "appName":appName})
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
                userID = [item["metadata"]["userID"]]
                instanceID = [item["metadata"]["instanceID"]]
                runID = [item["metadata"]["runID"]]
                timestamp = [item["metadata"]["timestamp"]]
                stageID = [item["metadata"]["stageID"]]
                appName = [item["metadata"]["appName"]]
            # Creat new row data
            dfi = pd.DataFrame({"confidence":confidence,
                                    "userID":userID,
                                    "instanceID":instanceID,
                                    "runID":runID,
                                    "timestamp":timestamp,
                                    "stageID":stageID,
                                    "appName":appName})
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
                userID = [item["metadata"]["userID"]]
                instanceID = [item["metadata"]["instanceID"]]
                runID = [item["metadata"]["runID"]]
                timestamp = [item["metadata"]["timestamp"]]
                stageID = [item["metadata"]["stageID"]]
                appName = [item["metadata"]["appName"]]
            # Creat new row data
            dfi = pd.DataFrame({"accuracy":accuracy,
                                    "userID":userID,
                                    "instanceID":instanceID,
                                    "runID":runID,
                                    "timestamp":timestamp,
                                    "stageID":stageID,
                                    "appName":appName})
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
            if report[stage][metric_name][instance] < min_value:
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

def objectDetectionParser(item, parser_conf):
    try:
        metric_list = parser_conf["metric"]
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
            userID = [item["metadata"]["userID"]]
            instanceID = [item["metadata"]["instanceID"]]
            runID = [item["metadata"]["runID"]]
            timestamp = [item["metadata"]["timestamp"]]
            stageID = [item["metadata"]["stageID"]]
            appName = [item["metadata"]["appName"]]
        # Creat new row data
        row_dict = {"userID":userID,
                    "instanceID":instanceID,
                    "runID":runID,
                    "timestamp":timestamp,
                    "stageID":stageID,
                    "appName":appName}
        row_dict.update(metric_cols)
        inf_df = pd.DataFrame(row_dict)
        return inf_df
    except Exception as e:
        logging.error("Error {} while parsing data in objectDetectionParser: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None

def agg_switch(switch, metric, aggregate_method):
    if aggregate_method == "mean":
        sum_value = 0
        count = 0
        for key in switch:
            flow = switch[key]
            if metric in flow:
                sum_value += flow[metric]
                count+=1
        if count != 0:
            return sum_value/count
        else:
            return 0
    if aggregate_method == "max":
        max_value = float('-inf')
        for key in switch:
            flow = switch[key]
            if metric in flow:
                if flow[metric] > max_value:
                    max_value = flow[metric]
        return max_value
    if aggregate_method == "min":
        min_value = float('inf')
        for key in switch:
            flow = switch[key]
            if metric in flow:
                if flow[metric] < min_value:
                    min_value = flow[metric]
        return min_value
    if aggregate_method == "sum":
        sum_value = 0
        for key in switch:
            flow = switch[key]
            if metric in flow:
                sum_value += flow[metric]
        return sum_value


def aggregate_switch(switch, config, prefix):
    result = {}
    for metric in config:
        metric_name = metric["name"]
        agg_med = metric["aggregate"]
        result[prefix+str(metric_name)] = [agg_switch(switch, metric_name, agg_med)]
    return result

def sdnParser(item, parser_conf):
    try:
        switch_df = pd.DataFrame()
        metric_list = parser_conf["metric"]
        if "flow" in metric_list:
            flowstat_config = metric_list["flow"]
        if "port" in metric_list:
            portstat_config = metric_list["port"]
        if "metadata" in item:
            userID = [item["metadata"]["userID"]]
            instanceID = [item["metadata"]["instanceID"]]
            runID = [item["metadata"]["runID"]]
            timestamp = [item["metadata"]["timestamp"]]
            stageID = [item["metadata"]["stageID"]]
            appName = [item["metadata"]["appName"]]
        # Creat new row data
        metadata_dict = {"userID":userID,
                    "instanceID":instanceID,
                    "runID":runID,
                    "timestamp":timestamp,
                    "stageID":stageID,
                    "appName":appName}
        switches = copy.deepcopy(item)
        switches.pop("metadata")
        for key in switches:
            row_switch = {}
            row_switch["switch"] = key
            switch = switches[key]
            row_switch.update(aggregate_switch(switch["FlowStats"], flowstat_config, "flow_"))
            row_switch.update(aggregate_switch(switch["PortStats"], portstat_config, "port_"))
            row_switch["agg_byte_count"] = [switch["Aggregate"]["byte_count"]]
            row_switch["agg_packet_count"] = [switch["Aggregate"]["packet_count"]]
            row_switch["agg_flow_count"] = [switch["Aggregate"]["flow_count"]]
            row_switch.update(metadata_dict)
            dfi = pd.DataFrame(row_switch)
            # concat new row data to result dataframe 
            switch_df = pd.concat([switch_df, dfi], ignore_index=True)
        return switch_df
    except Exception as e:
        logging.error("Error {} while parsing data in objectDetectionParser: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None
    
# def OCParser(item, parser_conf):
#     try:
#         metric_df = pd.DataFrame()
#         metric_list = parser_conf["metric"]

#         if "metadata" in item:
#             print(f"This is meta data received: {item['metadata']}")
#             # userID = [item["metadata"]["userID"]]
#             # instanceID = [item["metadata"]["instanceID"]]
#             # runID = [item["metadata"]["runID"]]
#             timestamp = [item["metadata"]["timestamp"]]
#             stageID = [item["metadata"]["stageID"]]
#             appName = [item["metadata"]["appName"]]
#             role = [item["metadata"]["role"]]
#         # Creat new row data
#         qoa_data = copy.deepcopy(item["quality"])
#         row_metric = {}
#         for category_key in list(metric_list.keys()):
#             if category_key in qoa_data:
#                 category = metric_list[category_key]
#                 for metric in category:
#                     max_value = -1
#                     if category_key == "inference":
#                         for instance_key in list(qoa_data[category_key].keys()):
#                             instance = qoa_data[category_key][instance_key]
#                             if metric["name"] in instance:
#                                 if instance[metric["name"]]["value"] > max_value:
#                                     max_value = instance[metric["name"]]["value"]
#                     else:
#                         for stage_key in list(qoa_data[category_key].keys()):
#                             stage = qoa_data[category_key][stage_key]
#                             if metric["name"] in stage:
#                                 for instance in list(stage[metric["name"]].keys()):
#                                     if metric["name"] == "responseTime":
#                                         value = stage[metric["name"]][instance][metric["name"]]
#                                     else:
#                                         value = stage[metric["name"]][instance]
#                                     if value > max_value:
#                                         max_value = value
#                     if max_value != -1:
#                         row_metric[metric["name"]] = [max_value]

#         metadata_dict = {
#                     # "userID":userID,
#                     # "instanceID":instanceID,
#                     "runID":runID,
#                     "timestamp":timestamp,
#                     "stageID":stageID,
#                     "appName":appName,
#                     "role":role}
#         result = copy.deepcopy(row_metric) 
#         row_metric.update(metadata_dict)
        
#         dfi = pd.DataFrame(row_metric)
#         if role == ["client"]:
#             file_path = parser_conf["client"]
#         else:
#             file_path = parser_conf["mlProvider"]
#         # if file does not exist write header 
#         if not os.path.isfile(file_path):
#             dfi.to_csv(file_path, header='column_names')
#         else: # else it exists so append without writing the header
#             dfi.to_csv(file_path, mode='a', header=False)

        
#         # for key in switches:
#         #     row_switch = {}
#         #     row_switch["switch"] = key
#         #     switch = switches[key]
#         #     row_switch.update(aggregate_switch(switch["FlowStats"], flowstat_config, "flow_"))
#         #     row_switch.update(aggregate_switch(switch["PortStats"], portstat_config, "port_"))
#         #     row_switch["agg_byte_count"] = [switch["Aggregate"]["byte_count"]]
#         #     row_switch["agg_packet_count"] = [switch["Aggregate"]["packet_count"]]
#         #     row_switch["agg_flow_count"] = [switch["Aggregate"]["flow_count"]]
#         #     row_switch.update(metadata_dict)
#         #     dfi = pd.DataFrame(row_switch)
#         #     # concat new row data to result dataframe 
#         #     switch_df = pd.concat([switch_df, dfi], ignore_index=True)
#         return result
#     except Exception as e:
#         logging.error("Error {} while parsing data in objectDetectionParser: {}".format(type(e),e.__traceback__))
#         traceback.print_exception(*sys.exc_info())
#         return None, None

def OCParser(item, parser_conf):
    try:
        metric_df = pd.DataFrame()
        metric_list = parser_conf["metric"]
        if "metadata" in item:
            client_id = [item["metadata"]["client_id"]]
            instance_name = [item["metadata"]["instance_name"]]
            instances_id = [item["metadata"]["instances_id"]]
            timestamp = [item["metadata"]["timestamp"]]
            stage_id = [item["metadata"]["stage_id"]]
            application = [item["metadata"]["application"]]
            role = [item["metadata"]["role"]]
        # Creat new row data
        qoa_data = copy.deepcopy(item["quality"])
        row_metric = {}
        for category_key in list(metric_list.keys()):
            if category_key in qoa_data:
                category = metric_list[category_key]
                for metric in category:
                    max_value = -1
                    if category_key == "inference":
                        for instance_key in list(qoa_data[category_key].keys()):
                            instance = qoa_data[category_key][instance_key]
                            if metric["name"] in instance:
                                if instance[metric["name"]]["value"] > max_value:
                                    max_value = instance[metric["name"]]["value"]
                    else:
                        for stage_key in list(qoa_data[category_key].keys()):
                            stage = qoa_data[category_key][stage_key]
                            if metric["name"] in stage:
                                for instance in list(stage[metric["name"]].keys()):
                                    if metric["name"] == "responseTime":
                                        value = stage[metric["name"]][instance][metric["name"]]
                                    else:
                                        value = stage[metric["name"]][instance]
                                    if value > max_value:
                                        max_value = value
                    if max_value != -1:
                        row_metric[metric["name"]] = [max_value]

        metadata_dict = {"client_id":client_id,
                    "instance_name":instance_name,
                    "instances_id":instances_id,
                    "timestamp":timestamp,
                    "stage_id":stage_id,
                    "application":application,
                    "role":role}
        result = copy.deepcopy(row_metric) 
        row_metric.update(metadata_dict)
        
        dfi = pd.DataFrame(row_metric)
        if role == ["client"]:
            file_path = parser_conf["client"]
        else:
            file_path = parser_conf["mlProvider"]
        # if file does not exist write header 
        if not os.path.isfile(file_path):
            dfi.to_csv(file_path, header='column_names')
        else: # else it exists so append without writing the header
            dfi.to_csv(file_path, mode='a', header=False)

        
        # for key in switches:
        #     row_switch = {}
        #     row_switch["switch"] = key
        #     switch = switches[key]
        #     row_switch.update(aggregate_switch(switch["FlowStats"], flowstat_config, "flow_"))
        #     row_switch.update(aggregate_switch(switch["PortStats"], portstat_config, "port_"))
        #     row_switch["agg_byte_count"] = [switch["Aggregate"]["byte_count"]]
        #     row_switch["agg_packet_count"] = [switch["Aggregate"]["packet_count"]]
        #     row_switch["agg_flow_count"] = [switch["Aggregate"]["flow_count"]]
        #     row_switch.update(metadata_dict)
        #     dfi = pd.DataFrame(row_switch)
        #     # concat new row data to result dataframe 
        #     swith_df = pd.concat([swith_df, dfi], ignore_index=True)
        return result
    except Exception as e:
        logging.error("Error {} while parsing data in objectDetectionParser: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None