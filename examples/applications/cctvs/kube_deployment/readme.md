# Step to run object detection example

- Note: this example include Yolov5 and Yolov8 trained models (large files ~1GB) and their wrappers for a stable version of [Ultralytics](https://github.com/ultralytics)'s Yolo inference library.
Make sure the structure is as follow:
```
├── artifact
├── example
│   ├── application
│   │   ├── cctvs
│   │   │   ├── ...
├── lib
│   ├── externalLib
│   ├── yolo
│   ├── ...
│   ├── modules
│   ├── services
├── ...
└── .gitignore
```
### Setting up Conda environment 

- Install the environment with anaconda3 using environment.yml
- This virtual environment will be used throughout this example.
> Modify the environment.yml with your suitable prefix
```
conda env create  --file environment-<python_version>.yml --name <env_name>
conda activate <env_name>       # enable conda virtual env
```


### Note on local dependencies
Currently some codes use $ROHE_ROOT_DIR/lib/*.py. Thus, the follow path may need to be set:
```
export PYTHONPATH=$ROHE_ROOT_DIR
```

### Running Observation Registration Service
> Open the first terminal console
- Enable the environment with anaconda3

- Navigate to services/observation/
- To start the Rohe Observation Service, run:
```bash
$ python roheObservationServiceV3.py
```
- This service is used to register applications, QoaClients and start observation agent

The data of application registered is send to MongoDB.
To observe metric from QoaClients, we need to run the Observation Agent.
The metric will also be stored in MongoDB


To start the Observation Agent Service, run (from another terminal console):
```bash
$ ./startAgent.sh
```

### Start edge-inference-server
> Open another terminal console 
- Enable the environment with anaconda3
- Navigate to examples/applications/cctvs/kube_deployment/edge-inference-server

- Environment setup (if conda env failed)
```bash
$ pip install -r requirements.txt
```
- Note: You only need to run `Environment setup` if you fail to enable conda environment in previous step

- Run edge-inference-server: 
```bash
$ python server.py
```
- The source code will clone Yolov5 as an external library (to folder `lib/externalLib`) if it does not exist, and download trained models to folder `artifact`.

### Start pre-processing server
> Open another terminal console 
- Enable the environment with anaconda3
- Navigate to example/application/cctvs/kube_deployment/preprocessor

- Environment setup (if conda env failed)
- Run pre-processing server: 
```bash
$ python preprocessor.py
```

### Start web server
> Open another terminal console 
- Enable the environment with anaconda3
- Navigate to example/application/cctvs/kube_deployment/web-server
- Environment setup (if conda env failed)
- Run web server:
```bash
$ python web_server.py
```



### Start client
> Open another terminal console 
- Navigate to example/application/cctvs/kube_deployment/client
- Run client:
```bash
$ python client.py
```

> Note: The QoAClient in this service will register with Observation service by default
