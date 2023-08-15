import pandas as pd
import logging, copy
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)

import traceback,sys

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
    
def train_local_outlier_factor(historical_data, n_neighbors = 20):
    # Train Local Ourlier Factor model
    try:
        model_lof = LocalOutlierFactor(n_neighbors=n_neighbors)
        model_lof.fit(historical_data)
        return model_lof
    except Exception as e:
        logging.error("Error {} while training isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def detect_local_outlier_factor(model_lof, stream_data):
    # Detect outlier in stream data
    try:
        """return 1: inlier; return -1: outlier"""
        return (model_lof.predict(stream_data))
    except Exception as e:
        logging.error("Error {} while predicting isolation forest: {}".format(type(e),e.__traceback__))
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
        print(dfs[key])
    return dfs,  model
