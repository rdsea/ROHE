


### structure of http request to image info service
#### Command: Get
no info required, just get image right away

#### Command: Add
Method: post

URL: host:port/image_info_service
Data:
{
    "command": "add",
    "request_id": ,
    "timestamp": ,
    "device_id": ,
    "image_url": ,
} 

sample: requests.post(image_info_service_url, data=data)

#### Command: completed
