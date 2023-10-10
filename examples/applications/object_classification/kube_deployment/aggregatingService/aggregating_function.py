import numpy as np


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