import pandas as pd
import logging, copy
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)
from sklearn.model_selection import train_test_split
import traceback,sys

############################################# FUNCTION #############################################

def train_isolation_forest(historical_data, feature, random_seed = 1, contamination = 0.05):
    # Train Isolation Forest model
    try:
        model_if = IsolationForest(contamination=float(contamination),random_state=random_seed)
        model_if.fit(historical_data[feature])
        return model_if
    except Exception as e:
        logging.error("Error {} while training isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

    
def train_local_outlier_factor(historical_data, feature, n_neighbors = 2, novelty=True):
    # Train Local Ourlier Factor model
    try:
        model_lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=novelty)
        model_lof.fit(historical_data[feature].values)
        return model_lof
    except Exception as e:
        logging.error("Error {} while training local outlier factor: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None
    

def detect_local_outlier_factor(data, feature, n_neighbors = 2, novelty=True):
    # data: dataFrame - input data
    # feature: list - features to differentiate sample
    # Detect outlier in stream data
    try:
        # split train - test data following time oder
        train, test = train_test_split(data, test_size=0.1, shuffle=False)
        # train model on train dataset
        model_lof = train_local_outlier_factor(train, feature, n_neighbors, novelty)

        # make predictions
        """return 1: inlier; return -1: outlier"""
        # add prediction score to dataFrame
        test['scores']=model_lof.decision_function(test[feature].values)
        # add anomaly label to dataFrame
        test['anomaly']=model_lof.predict(test[feature].values)
        # return result and model
        return test, model_lof
    except Exception as e:
        logging.error("Error {} while predicting with local outlier factor: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def detect_isolation_forest(data, feature, random_seed = 1, contamination = 0.05):
    # data: dataFrame - input data
    # feature: list - features to differentiate sample
    # Detect outlier in stream data
    try:
        # split train - test data following time oder
        train, test = train_test_split(data, test_size=0.1, shuffle=False)
        # train model on train dataset
        model_if = train_isolation_forest(train, feature, random_seed, contamination)

        # make predictions
        """return 1: inlier; return -1: outlier"""
        # add prediction score to dataFrame
        test['scores']=model_if.decision_function(test[feature])
        # add anomaly label to dataFrame
        test['anomaly']=model_if.predict(test[feature])
        return test, model_if
    except Exception as e:
        logging.error("Error {} while predicting isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None
    
def sdn_malware_detect(data, feature, function=0, configuration=None):
    # data: dataFrame - input data
    # feature: list - features to differentiate sample
    # configuration: function configuration
    try:
        # group data by switch and flow for detect anomaly 
        dfs = {k:v for k, v in data.groupby(['switch', 'in_port', 'eth_dst'])}
        # metric need to be evaluate for detecting anomaly
        sdn_shift_feature = ["packet_count", "byte_count"]
        # init final dataFrame to convey results
        final_df = pd.DataFrame()
        model = None
        # iterate dataFrame in grouped dataFrame
        for key in dfs:
            # only edit on copy dataFrame
            df = copy.deepcopy(dfs[key])
            
            # Normalize data before apply ML detection
            # Todo: time interval -> configuration
            for metric in sdn_shift_feature:
                df[metric] = df[metric] - df[metric].shift(10, fill_value=0)
                df[metric] = (df[metric] - df[metric].min())/(df[metric].max()-df[metric].min())
            # Transform timestamp to time interval
            # Todo: time interval -> configuration
            df["time"] = df["timestamp"] - df["timestamp"].shift(10, fill_value=0)
            df = df.iloc[10:]

            # add time to feature to differentiate sample
            new_feature = ["time"]
            for i in feature:
                new_feature.append(i)

            # apply detection when buffer data have significant amount of data
            # Todo: threshold -> configuration
            if len(df.index) > 80:
                if function == 0:
                    dfs[key], model = detect_isolation_forest(df, new_feature)
                elif function == 1:
                    dfs[key], model = detect_local_outlier_factor(df, new_feature)
                logging.debug(dfs[key])
                # concat result to final dataFrame
                final_df = pd.concat([final_df, dfs[key]], ignore_index=True)
        # only return final dataFrame when ML detection is applied
        if model != None:
            return final_df,  model
        else:
            return None, None
    except:
        logging.error("Window processing error in sdn_detect_isolation_forest")
        return None, None
    
def sdn_detect_isolation_forest(data, feature, configuration=None):
    return sdn_malware_detect(data, feature, function=0)

def sdn_detect_local_outlier_factor(data, feature, configuration=None):
    return sdn_malware_detect(data, feature, function=1)
    
############################################# PARSER #############################################

def sdnParser(item, parser_conf):
    # item: data from network controller
    # parser_config: configuration of parser for SDN application
    try:
        switch_df = pd.DataFrame()
        # get metric list from parser configuration
        metric_list = parser_conf["metric"]

        # get flow metric config if exist
        if "flow" in metric_list:
            flowstat_config = metric_list["flow"]

        # processing in copy data
        switches = copy.deepcopy(item)

        # init metadata for every row data
        if "metadata" in item:
            user_id = [item["metadata"]["user_id"]]
            instance_id = [item["metadata"]["instance_id"]]
            run_id = [item["metadata"]["run_id"]]
            timestamp = [item["metadata"]["timestamp"]]
            stage_id = [item["metadata"]["stage_id"]]
            application_name = [item["metadata"]["application_name"]]
            # remove metadata before processing
            switches.pop("metadata")

        # Creat new row data as dictionary -> dataframe
        metadata_dict = {"user_id":user_id,
                    "instance_id":instance_id,
                    "run_id":run_id,
                    "timestamp":timestamp,
                    "stage_id":stage_id,
                    "application_name":application_name}
        
        # iterate switches in data
        for key in switches:
            switch = switches[key]
            flow_data = switch["FlowStats"]
            # iterate flows in switch
            for flow_key in flow_data:
                row_switch = {}
                row_switch["switch"] = [key]
                result = {}
                result["switch"] = [key]
                metrics = flow_data[flow_key]
                # get in_port and eth_dst from flow key
                flow_id = flow_key.split("_")
                in_port = flow_id[0]
                componentIP = flow_id[1]
                # add features to data row
                result["in_port"] = [in_port]
                result["eth_dst"] = [componentIP]
                # add metrics to data row
                for metric in flowstat_config:
                    metric_name = metric["name"]
                    result[str(metric_name)] = [metrics[metric_name]]
                # update row data
                row_switch.update(result)
                row_switch.update(metadata_dict)
                # convert row data to pandas
                dfi = pd.DataFrame(row_switch)
                # concat pandas dataFrame to the final dataFrame
                switch_df = pd.concat([switch_df, dfi], ignore_index=True)
        return switch_df
    except Exception as e:
        logging.error("Error {} while parsing data in sdnParser: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None, None
