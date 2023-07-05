import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
import traceback,sys

def train_isolation_forest(historical_data, random_seed = 1, contamination = 0.05):
    try:
        model_if = IsolationForest(contamination=float(contamination),random_state=random_seed)
        model_if.fit(historical_data)
        return model_if
    except Exception as e:
        print("[ERROR] - Error {} while training isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def detect_isolation_forest(model_if, stream_data):
    try:
        """return 1: inlier; return -1: outlier"""
        return (model_if.predict(stream_data))
    except Exception as e:
        print("[ERROR] - Error {} while predicting isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None
    
def train_local_outlier_factor(historical_data, n_neighbors = 20):
    try:
        model_lof = LocalOutlierFactor(n_neighbors=n_neighbors)
        model_lof.fit(historical_data)
        return model_lof
    except Exception as e:
        print("[ERROR] - Error {} while training isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None

def detect_local_outlier_factor(model_lof, stream_data):
    try:
        """return 1: inlier; return -1: outlier"""
        return (model_lof.predict(stream_data))
    except Exception as e:
        print("[ERROR] - Error {} while predicting isolation forest: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
        return None