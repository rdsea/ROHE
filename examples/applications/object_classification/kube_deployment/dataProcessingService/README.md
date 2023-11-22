processing service need to have the url of the task coordinator to request to get image from
then make inference request to a set of inference service (depend on param set)
may also be changed to a rest service, so that we can request to change its set of inference service to request to

### structure of request to inference service
Method: post
URL: host:port/inference
Data:
data = {
    'command': 'predict'
    'meta_data': {
        'request_id':
        'shape':
        'dtype':
    }
} 
Files:
    - file =  {'image': ('image', image_bytes, 'application/octet-stream')}
    - `image_bytes` (binary, required): The image data in binary format.

sample: requests.post(inference_service_url, data=data, files=files)


### send info to aggregating service