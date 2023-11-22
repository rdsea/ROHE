# Inference Service

_Description_: This microservice is responsible for executing machine learning inference on the processed images. It receives an image, processes it using the designated machine learning model, and returns the inferred results. This service works in tandem with the processing service to ensure images are analyzed and results are forwarded to the aggregation service.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Setup & Installation](#setup--installation)
- [Dockerization](#dockerization)
- [Running the Service](#running-the-service)
- [API Endpoints](#api-endpoints)


## Prerequisites
- Python: Programming language used for the service logic.
- Docker: Containerization platform to deploy and run the services.
- Tensorflow: Deep learning framework used for machine learning tasks.
- MinIO: Object storage server with Amazon S3-compatible API, used for storing and retrieving images.
- Kafka: Distributed event streaming platform used for sending results to the aggregation service (via Kafka topics) or directly saving results to MongoDB without aggregation.
- Database - MongoDB: A NoSQL database used for storing application data, including direct results from the inference service.

## Configuration
### 1. Configuration file structure
(Image update later)

### 2. Environment Variables
Set the path to ROHE local repo directory as environment variable (in .env file) (eg: ROHE=/home/vtn/aalto-internship/ROHE)

### 3. Runtime Parameters (Using argparse)

Usage: `python server.py [OPTIONS]`

| Option            | Description                                                      | Sample Value             |
|-------------------|------------------------------------------------------------------|--------------------------|
| `--conf`          | Path to the configuration file for the Inference Service         | `/path/to/config.json`   |
| `--port`          | Specifies the port on which the Inference Service will listen    | `30005`                   |
| ...               | ...                                                              | ...                      |

Example:
`python server.py --config ./configurations/config.json --port 30005`


## Setup & Installation
### 1. Clone the repository
- git clone https://github.com/rdsea/ROHE.git
- cd examples/applications/object_classification/kube_deployment/inferenceService

### 2. Install Dependencies
pip install -r requirements.txt

## Running the Service


## API Endpoints : /inference
#### Command: Predict
##### Request
Method: post
URL: host:port/inference
Data:
{
    'command': 'predict'
    'metadata': (JSON string, required): A JSON string containing metadata about the request. Structure: {"request_id": "12345", "shape": "256x256 "dtype": "float32"}
} 
Files:
    {'image': ('image', image_bytes, 'application/octet-stream')}
    - `image_bytes` (binary, required): The image data in binary format.

##### Response

The API provides the following responses:

- **Status Code: 200 OK** - The request was successful.

    Example Success Response:

    ```json
    {
        "class": , 
        "confidence_level": , 
        "prediction":}
    }
    ```

result = json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}


- **Status Code: 400 Bad Request** - If the request is missing required parameters or has invalid data.

- **Status Code: 500 Internal Server Error** - If there's an issue on the server side.

### 1. Post

#### Command: predict
##### Request Parameters

- `command` (string, required): Set to "predict" to indicate that you want to make a prediction.
- `metadata` (JSON string, required): A JSON string containing metadata about the request.

##### Request Body

- `image` (binary, required): The image data in binary format, should be included as a file.

##### Example Request

```http
POST /inference
Content-Type: multipart/form-data

Command: predict
Metadata: {"request_id": "12345", "shape": "256x256", "dtype": "float32"}
: [binary image data]

```

##### Response

The API provides the following responses:

- **Status Code: 200 OK** - The request was successful.

    Example Success Response:

    ```json
    {
        "class": , 
        "confidence_level": , 
        "prediction":}
    }
    ```

result = json.dumps({'response': response}), 200, {'Content-Type': 'application/json'}


- **Status Code: 400 Bad Request** - If the request is missing required parameters or has invalid data.

- **Status Code: 500 Internal Server Error** - If there's an issue on the server side.