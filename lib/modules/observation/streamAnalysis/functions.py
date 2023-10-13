import pandas as pd
import logging, copy
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)

import traceback,sys

def dummy_function(data):
    print(data)
    return None

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

def detect_isolation_forest(data, feature, random_seed = 1, contamination = 0.05):
    # Detect outlier in stream data
    try:
        """return 1: inlier; return -1: outlier"""
        model_if = train_isolation_forest(data, feature, random_seed, contamination)
        data['scores']=model_if.decision_function(data[feature])
        data['anomaly']=model_if.predict(data[feature])
        return data, model_if
    except Exception as e:
        logging.error("Error {} while predicting isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None
    
def train_local_outlier_factor(historical_data, feature, n_neighbors = 2, novelty=True):
    # Train Local Ourlier Factor model
    try:
        model_lof = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=novelty)
        model_lof.fit(historical_data[feature].values)
        return model_lof
    except Exception as e:
        logging.error("Error {} while training isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def detect_local_outlier_factor(data, feature, n_neighbors = 2, novelty=True):
    # Detect outlier in stream data
    try:
        model_lof = train_local_outlier_factor(data, feature, n_neighbors, novelty)
        """return 1: inlier; return -1: outlier"""
        data['scores']=model_lof.decision_function(data[feature].values)
        data['anomaly']=model_lof.predict(data[feature].values)
        return data, model_lof
    except Exception as e:
        logging.error("Error {} while predicting with local outlier factor: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def sdn_detect_isolation_forest(data, feature):
    dfs = {k:v for k, v in data.groupby('switch')}
    sdn_shift_feature = ["agg_byte_count", "agg_packet_count","flow_packet_count", "flow_byte_count"]
    for key in dfs:
        df = copy.deepcopy(dfs[key])
        for metric in sdn_shift_feature:
            df[metric] = df[metric] - df[metric].shift(1, fill_value=0)
        df = df.iloc[1:]
        dfs[key], model = detect_isolation_forest(df, feature)
        logging.debug(dfs[key])
    return dfs,  model

def sdn_detect_local_outlier_factor(data, feature):
    dfs = {k:v for k, v in data.groupby('switch')}
    sdn_shift_feature = ["agg_byte_count", "agg_packet_count","flow_packet_count", "flow_byte_count"]
    final_df = pd.DataFrame()
    for key in dfs:
        df = copy.deepcopy(dfs[key])
        for metric in sdn_shift_feature:
            df[metric] = df[metric] - df[metric].shift(1, fill_value=0)
        df = df.iloc[1:]
        dfs[key], model = detect_local_outlier_factor(df, feature)
        logging.debug(dfs[key])
        final_df = pd.concat([final_df, dfs[key]], ignore_index=True)
    print(final_df)
    return final_df,  model
