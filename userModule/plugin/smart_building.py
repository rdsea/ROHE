from typing import List, Dict, Union
import pandas as pd
import traceback

def accurate_explainability(row, k: int) -> int:
    try:
        ground_truth = row['ground_truth']
        inference_data = row['inf_result']
        if isinstance(inference_data, str):
            inference_data = dict(eval(inference_data))
        # Get the top k predictions
        top_k_predictions = dict(sorted(inference_data.items(), key=lambda x: x[1], reverse=True)[:k])
        # Calculate accuracy
        top_k_classes = list(top_k_predictions.keys())[:k]
        if ground_truth in top_k_classes:
            return 1
        return 0
    except Exception as e:
        print(f"Error evaluating explainability accuracy: {e}")
        print(traceback.format_exc())
        return 0


def get_top_k_predictions(data, top_k: int = 5) -> List[str]:
    top_k = sorted(data.items(), key=lambda item: item[1], reverse=True)[:top_k]
    top_k_keys = [key for key, _ in top_k]
    return top_k_keys

def get_worst_k_predictions(data, worst_k: int = 5) -> List[str]:
    worst_k = sorted(data.items(), key=lambda item: item[1])[:worst_k]
    worst_k_keys = [key for key, _ in worst_k]
    return worst_k_keys

def explainability_sli_check(monitoring_data: Union[str, pd.DataFrame], ground_truth:Union[str:pd.DataFrame], top_k: int = 1, window_size: int = 5, step_size: int = 1) -> float:
    if isinstance(monitoring_data, pd.DataFrame) and isinstance(ground_truth, pd.DataFrame):
        data_df = monitoring_data[monitoring_data['explainability'] == True]
        accuracy_df = ground_truth
        explainability_df = pd.merge(accuracy_df, data_df, on='query_id', how='inner')
        explainability_df['top_k_explainability'] = explainability_df.apply(lambda row: accurate_explainability(row, top_k), axis=1)
        return explainability_df['top_k_explainability'].mean()