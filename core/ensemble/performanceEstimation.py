# Abstract Function for Evaluating Performance of an Ensemble based on Performance of Microservices
from typing import List, Dict
import argparse, os, sys, copy
import pandas as pd
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib.roheUtils import list_files, load_config

def Evaluator(elementPerforamces: List[Dict], params: dict) ->  dict:
    """
    Input data
    elementPerforamces = [
        {
            "bicycle": {                                                        # <data condition/quality>
                "accuracy": 0.909836066,
                "min_confidence": 0.30376032,
                "avg_confidence": 0.919143788,
                "percentage_confidence_over_50": 0.968903437,
                "avg_confidence_correct_prediction": 0.948153521,
                "avg_confidence_incorrect_prediction": 0.800052025,
                "min_response_time": 0.000356197,
                "max_response_time": 0.043570518,
                "avg_response_time": 0.000626373
            }
        }               
    ]
    """
    ensemblePerformance = {}
    return ensemblePerformance

def metric_process(cur, temp, operator):
    if operator == "max":
        if temp > cur:
            return temp
        else:
            return cur
    if operator == "min":
        if temp < cur:
            return temp
        else:
            return cur

# Example for Object Detection Application
def ODEvaluator(elementPerforamces: List[Dict], params: dict) ->  dict:
    ensemblePerformance = copy.deepcopy(elementPerformances[0])
    for i in range(1,len(ensemblePerformance)):
        for quality in ensemblePerformance:
            data = ensemblePerformance[quality]
            for metric_key in params["metric"]:
                data[metric_key] = metric_process(data[metric_key], elementPerforamces[i][quality][metric_key],params["metric"][metric_key])
    return ensemblePerformance

def generate_performance_dict(row_data, params):
    data_quality = row_data[params["data_quality"]]
    metrics = params["metric"]
    row_performance = {}
    row_performance[data_quality] = {}
    for metric_key in metrics:
        row_performance[data_quality][metric_key] = row_data[metric_key]
    return row_performance

def load_performance(folder_path, params):
    files = list_files(folder_path)
    elementPerformances = []
    for file_name in files:
        file_path = files[file_name]
        df = pd.read_csv(file_path, index_col=None)
        performance = {}
        for index, row in df.iterrows():
            row_dict = generate_performance_dict(row, params)
            performance.update(row_dict)
        elementPerformances.append(performance)
    return elementPerformances


################################################################ TEST ################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Abstract Function for Estimate Performance of Ensemble")
    parser.add_argument('--data', type=str, help='data folder', default="/core/ensemble/raw_data/")
    parser.add_argument('--param', type=str, help='parameter', default="./params.yaml")

    args = parser.parse_args()
    folder_path = ROHE_PATH+args.data
    params = load_config(args.param)
    elementPerformances = load_performance(folder_path, params)
    ensemblePerformance = ODEvaluator(elementPerformances, params)
    print(ensemblePerformance)
    
        
