To run edge-inference-server, you must download yolov5 and yolov8 and unzip them in "lib" folder
Link: https://drive.google.com/file/d/1oI8ahTMELdbdAoBWgqmPZnMjJ43hoCvJ/view?usp=drive_link, https://drive.google.com/file/d/1RyyuJwn9t1LpWt6QE25j13HrJZ3cCZwK/view?usp=drive_link

### Setting up Conda environment 

- Install the environment with anaconda3 using environment.yml
> Modify the environment.yml with your suitable prefix
```
conda env create  --file environment.yml
```
- Enable the environemnt with anaconda3

### Note on local dependencies
Currently some codes use $ROHE_ROOT_DIR/lib/*.py. Thus, the follow path may need to be set:
```
export PYTHONPATH=$ROHE_ROOT_DIR
```

### Running Observation Registration Service

The ORS is in $ROHE/services/observation 

- Start the Observation Registration Server: 
    - Navigate to services/observation/
    - Run `python roheRegistrationServiceV2.py`
    - This service is used to register application and QoaClient

### Start edge-inference-server

- Navigate to examples/applications/object_detection/kube_deployment/edge-inference-server
- Install dependencies for the inference server

- Run `python server.py`

    - The QoAClient in this service will register with Observation Registration Server by default

- Start pre-processing server
    - Navigate to example/application/object_detection/kube_deployment/preprocessor
    - Run `python preprocessor.py`

- Start web server
    - Navigate to example/application/object_detection/kube_deployment/web-server
    - Run `python web_server.py`
    - The QoAClient in this service will register with Observation Registration Server by default

The data of application registered is send to MongoDB.
To observe metric from QoaClients, we need to run the Observation Agent.
The metric will also be stored in MongoDB


- Start the Observation Agent Service: 
    - Navigate to services/observation/
    - Run `python roheAgentServiceV2.py`
    - Run `./startAgent.sh`


- Start client
    - Navigate to example/application/object_detection/kube_deployment/client
    - Run `python client.py`
