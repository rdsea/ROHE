# Application Deployment
Each application contains multiple microservices.
A microservice needs a deployment file (yaml) and a image (container image, e.g docker image) to be deployed on Kubernetes-like platform (K3s, KubeEdge, etc).

## Build a microservice
Source code of each microservice is stored in a separate folder with a Docker file. 
After building the image, it should be published in a public portal such as Dockerhub.
## Deployment file - yaml
The deployment should specify an image containing the application which is built and published. For example: minhtribk12/ml_ubuntu:1.0 in Dockerhub

The image is mention in the following configuration:
```yaml
    spec:
      containers:
      - image: minhtribk12/ml_ubuntu:1.0
        imagePullPolicy: Always
        name: mlserver
        ports:
        - containerPort: 5000
```

`imagePullPolicy` is set to Always to make sure it pulls newest image every time it starts the container. Port for communicate should be specify at `containerPort`. Note that the ports are only expose for internal network in same `namespace` in Kubernetes

The service is published to other component via Service Deployment:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ml-service
spec:
  selector:
    app: mlserver
  type: LoadBalancer
  ports:
  - port: 5000
    name: defaultport
    protocol: TCP
    targetPort: 5000
    nodePort: 30002
```

The type of service is specify as `LoadBalancer` make sure every coming requests are forwarded to the containers in a balance manner. `nodePort` specification allow the service exposes to external network with specific ports (>30000).

- Deploy an application and its service:
```bash
sudo kubectl apply -f <file_path>
```

## Communication among microservices
- For applications where the developer already defines and implements the service call (e.g. REST), the `configMap` is used to provide environment variables mapping with the service names. It usually includes the address of all tasks/services so the containerized service know where to call other services.
- For some applications where the developer only provide the functions and computation pipeline/graph without communication feature. We can use DAG and template service wrapper (image_build/core_function) to build containerized services which communicate via messages forming a pipeline/graph.
This module requires developer specify the computation pipeline in `json` format, example: `user_dag.json`. 

- <mark>DAG is also used for further calculation on communication overhead<mark>.
  - To do: 
    - Allow user to specify nodes/edges - done
    - Allow user to specify docker image/building file path - done
    - Allow user to define communication/gateway - missing service name
    - Auto build/pull docker images 
    - Auto deploy/update/remove deployments/services

## Application Profiling
- The script in the profiling folder (`profilingDeployment.py`) will load the user's pre-defined computation graph and deploy node by node (microservices) with the scales in "scale.txt". We can set different scales and profiling times by passing parameter when calling the script.
If the script is not executed in the K3s master node, we need a `key` stored in `key.txt`.
- At the same time, we must start sending requests to the deployed application and run a collector to collect monitoring data. The collector must query data from the specific channels and queues where the application sends its monitoring data to.


## Automate Deployment
- First, you need to generate deployment files from the pre-defined computation graph (`user_dag.json`), default deployment (`/default/deployment.yaml`), and default communication (`/default/config.json`) - if the communications between services are not specified.

  Execute the function `generateDeployment` in `init_from_dag.py` with file paths to the above three configurations.

  The deployment file will be generated and stored in the folders specified in `user_dag.json`
- Second, you need to create a profiling configuration `profiling_config.json` and specify Kube/K3s configuration, profiling time and service scales (the name of the service must match with node[value] in `user_dag.json`)

  Execute the function `profilingDeploy` in `profilingDeployment.py`

- An example with BTS is provided in `example/bts/bts_profiling.py`. You must copy utilities, profiling folders and init_from_dag.py to the same folder to make sure they can be imported.