


### structure of http request to task coordinator
#### Command: Get
no info required, just get image right away

#### Command: Add
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

#### Command: completed
