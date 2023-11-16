import numpy as np


# blending 
# ---------------------------------------------------------
def average_probability(data: list) -> dict:
    # print(f"This is the type of data: {type(data)}")

    if not data:
        print("Empty data, no aggregation needed.")
        return

    req_id = data[0]['request_id']
    # print(f"Request ID : {req_id}, len of the data: {len(data)}")
    
    # To store aggregated predictions, pipeline_ids, and inference_model_ids
    aggregated_predictions = []
    pipeline_ids = []
    inference_model_ids = []
    
    for entry in data:
        aggregated_predictions.append(entry['prediction'])
        pipeline_ids.append(entry['pipeline_id'])
        inference_model_ids.append(entry['inference_model_id'])
    
    mean_prediction: np.ndarray = np.mean(aggregated_predictions, axis=0)
    
    aggregated_result = {
        'request_id': req_id,
        'prediction': mean_prediction.tolist(),
        'pipeline_id': ','.join(pipeline_ids),
        'inference_model_id': ','.join(inference_model_ids)
    }

    # print(f"This is the aggregate result: {aggregated_result}")
    # print("End of aggregating process\n\n\n\n")
    return aggregated_result

def weighted_average_probability(data: list, weights: list) -> dict:
    if not data or not weights:
        print("Empty data or weights, no aggregation needed.")
        return

    req_id = data[0]['request_id']

    aggregated_predictions = []
    pipeline_ids = []
    inference_model_ids = []

    for entry, weight in zip(data, weights):
        weighted_prediction = np.array(entry['prediction']) * weight
        aggregated_predictions.append(weighted_prediction)
        pipeline_ids.append(entry['pipeline_id'])
        inference_model_ids.append(entry['inference_model_id'])

    mean_prediction = np.sum(aggregated_predictions, axis=0)

    aggregated_result = {
        'request_id': req_id,
        'prediction': mean_prediction.tolist(),
        'pipeline_id': ','.join(pipeline_ids),
        'inference_model_id': ','.join(inference_model_ids)
    }

    return aggregated_result

def rank_averaging(data: list) -> dict:
    if not data:
        print("Empty data, no aggregation needed.")
        return

    req_id = data[0]['request_id']
    aggregated_predictions = []
    pipeline_ids = []
    inference_model_ids = []

    for entry in data:
        aggregated_predictions.append(entry['prediction'])
        pipeline_ids.append(entry['pipeline_id'])
        inference_model_ids.append(entry['inference_model_id'])

    # Rank the predictions
    ranks = []
    for predictions in aggregated_predictions:
        ranks.append(np.argsort(np.argsort(predictions)))

    # Average the ranks
    average_ranks = np.mean(ranks, axis=0)

    # Convert ranks back into prediction values
    min_val = np.min(aggregated_predictions)
    max_val = np.max(aggregated_predictions)
    ranked_predictions = min_val + (max_val - min_val) * (average_ranks / len(data))

    aggregated_result = {
        'request_id': req_id,
        'prediction': ranked_predictions.tolist(),
        'pipeline_id': ','.join(pipeline_ids),
        'inference_model_id': ','.join(inference_model_ids)
    }

    return aggregated_result

# ---------------------------------------------------------

def majority_voting(data: list) -> dict:
    if not data:
        print("Empty data, no aggregation needed.")
        return

    req_id = data[0]['request_id']

    all_predictions = []
    pipeline_ids = []
    inference_model_ids = []

    for entry in data:
        all_predictions.append(entry['prediction'])
        pipeline_ids.append(entry['pipeline_id'])
        inference_model_ids.append(entry['inference_model_id'])

    # Assumes predictions are class labels
    majority_vote = [max(set(predictions), key=predictions.count) for predictions in zip(*all_predictions)]

    aggregated_result = {
        'request_id': req_id,
        'prediction': majority_vote,
        'pipeline_id': ','.join(pipeline_ids),
        'inference_model_id': ','.join(inference_model_ids)
    }

    return aggregated_result


# more functions
def median_averaging(data: list) -> dict:
    if not data:
        print("Empty data, no aggregation needed.")
        return

    req_id = data[0]['request_id']
    aggregated_predictions = []
    pipeline_ids = []
    inference_model_ids = []

    for entry in data:
        aggregated_predictions.append(entry['prediction'])
        pipeline_ids.append(entry['pipeline_id'])
        inference_model_ids.append(entry['inference_model_id'])

    median_prediction = np.median(aggregated_predictions, axis=0)

    aggregated_result = {
        'request_id': req_id,
        'prediction': median_prediction.tolist(),
        'pipeline_id': ','.join(pipeline_ids),
        'inference_model_id': ','.join(inference_model_ids)
    }

    return aggregated_result

