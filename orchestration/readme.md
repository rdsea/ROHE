# Orchestration Module
## 1. Resource
The framework manage the infrastructure resource by Node; application by Deployment; network routine by Service; and eviroment variable by ConfigMap.
- Node: physical node
- Deployment: each application has multiple microservices. Each service has its own Deployment setup specify: image, resource requirement, replicas, etc
- Service: each microservice is advertized with a service name within K3s network so that other services can communicate with it.
- ConfigMap: provide initial environment variable for docker containers of each deployment when starting.

## 2. Algorithm
Sub-module:
- Selecting node for each deployment
- Profiling, categorizing microservices
- Elastic scaling
