### structure of http request to ingestion server

Method: post
URL: host:port/ingestion
Data:
data = {
    'timestamp': 
    'device_id': 'aalso_cam_01'
    'meta_data': {
        'shape':
        'dtype':
    }
} 
Files:
    - file =  {'image': ('image', image_bytes, 'application/octet-stream')}
    - `image_bytes` (binary, required): The image data in binary format.

sample: requests.post(ingestion_service_url, data=data, files=files)


### structure of http request to task coordinator
Method: post
URL: host:port/task_coordinator
Data:
{
    "command": "add",
    "request_id": ,
    "timestamp": ,
    "device_id": ,
    "image_url": ,
} 

sample: requests.post(task_coordinator_url, data=data)