# ROHE
---

[![Documentation](https://img.shields.io/badge/Documentation-gray?logo=materialformkdocs)](https://rdsea.github.io/ROHE/)
![PyPI - Status](https://img.shields.io/pypi/status/rohe)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/rohe)
![PyPI - Version](https://img.shields.io/pypi/v/rohe)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rohe)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/format.json)](https://github.com/astral-sh/ruff)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/rdsea/rohe/python-ci.yml?logo=github&label=Github%20Actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)



---

ROHE is an orchestration framework for end-to-end machine learning serving on heterogeneous edge. 
The framework provides a set of services for monitoring, orchestration, and resource management of ML pipelines on edge devices.

Features:

- [Resource Optimization](src/rohe/orchestration/resource_management/): ROHE selects the optimal edge nodes for deploying microservices in ML pipelines based on resource requirements and availability. It also allows developers to implement their own resource allocation algorithms. Currently, ROHE supports application deployments on Kube-like environment (e.g., K3s and K8s). Publication: [On Optimizing Resources for Real-Time End-to-End Machine Learning in Heterogeneous Edges](https://onlinelibrary.wiley.com/doi/full/10.1002/spe.3383)
- [Observation Service](src/rohe/observation/): ROHE provides a service for monitoring and analyzing the performance of ML pipelines. It allows developers to register their applications, configure observation agents, collect metrics from running applications, and support runtime explainability. Publication: [Novel contract-based runtime explainability framework for end-to-end ensemble machine learning serving](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10555921), [Security orchestration with explainability for digital twins-based smart systems](https://research.aalto.fi/en/publications/security-orchestration-with-explainability-for-digital-twins-base).
Also see [QoA4ML](https://github.com/rdsea/QoA4ML) - a monitoring library for end-to-end ML applications.
- [Orchestration Service](src/rohe/orchestration/): ROHE provides set of algorithms for orchestrating runtime inferences by selecting the best ML services (ML models and edge nodes) or ensemble of ML services for running inference tasks. Developers can also implement their own orchestration algorithms as ROHE plugins to optimize the quality of service base on consumer-specific contexts. Publication: [Optimizing Multiple Consumer-specific Objectives in End-to-End Ensemble Machine Learning Serving](https://ieeexplore.ieee.org/abstract/document/10971860)

---
## High-level view


<figure>
<p style="text-align:center">
<img src="docs/img/animated.svg" alt="ROHE High-level View" width="1000"/>
</p>
<figcaption>
<p style="text-align:center">
Fig. ROHE High-level View
</p>
</figcaption>
</figure>

## Installation
### From PyPI
You can install ROHE from PyPI using pip:
```bash
pip install rohe
```

### From Source
You can also install ROHE from source. First, clone the repository:
```bash
git clone https://github.com/rdsea/ROHE.git
cd ROHE
pip install -e .
```

**Note:** Due to the continuous development of the required Python libraries, the installation may have some dependency conflicts.

## Structure of the repository
The repository is structured as follows:
```ROHE/
├── config/                  # Configuration files for ROHE services
├── datasets/                # Data generated from experiments or used in scientific publications
├── deployment/              # Deployment of external services (e.g., MongoDB, redis, etc.)
├── docs/                    # Documentation files
├── examples/                # Example applications (services and clients), and service contracts, etc.
├── src/                     # Source code of ROHE
│   ├── rohe/                # Main package of ROHE
│   │   ├── api/             # APIs for manage computation resources (will be further developed)
│   │   ├── common/          # Data models, abstractions, and utilities
│   │   ├── external/        # Connectors to other services and modules (e.g., k8s)
│   │   ├── lib/             # Utility functions and classes in ROHE
│   │   ├── messaging/       # For communication between ROHE services
│   │   ├── observation/     # Observation implementation
│   │   ├── orchestration/   # Orchestration implementation
│   │   ├── rohe_cli/        # Command line interface for ROHE
│   │   └── service/         # Deployment of ROHE services
│   │   └── service_registry/         # Manage service registration and discovery
│   │   └── storage/         # Connectors to storage services (e.g., MongoDB, MinIo, etc.)
│   └── system_setup/        # Setup system environment (e.g., K3s, Docker, etc. - under maintenance)
│   └── templates/           # Templates for data communicated between ROHE services
│   └── tests/               # Unit tests for ROHE (under development)
│   └── userModule/          # Extension modules implemented by users
├── other project files      # Readme, license, etc.

```

## 1. Observation Service

### 1.1 User Guide

- Prerequisite: before using Observation Agent, users need:
  - Database service (e.g., MongoDB)
  - Communication service (e.g., AMQP message broker)
  - Container environment (e.g., Docker)
  - Visualization service (e.g., Prometheus, Graphana - optional)
- Observation Service includes registration service and agent manager. Users can modify Observation Service configurations in `$ROHE_PATH/config/observationConfigLocal.yaml`.
  The configuration defines: - Protocols with default configurations for public (connector) and consume (collector) metrics. - Database configuration where metrics and application data/metadata are stored. - Container Image of the Observation Agent - Logging Level (debugging, warning, etc)
- To deploy Observation Service, use rohe-cli:

```bash
$ rohe-cli start observation-service
```

- Application Registration
  - Users can register the application using `rohe-cli`. Application metadata and related configurations will be saved to the Database
  - When register an end-to-end ML application, the users must provide application name (`app_name` - string), run ID (`run_id` - string), user ID (`user_id` - string), and send registration request to the Observation Service via its `url`.
  - The Observation Service will generate:
  - Application ID: `appID`
  - Database name: `db` for saving metric reports in runtime
  - Qoa configuration: `qoa_config` for reporting metrics

Example

```bash
$ rohe-cli observation register-app --app <application_name> --run <run_ID> --user <user_ID> --url <resigstration_service_url> --output_dir <folder_path_to_save_app_metadata>
```

- Then, users must implement QoA probes manually into the application. Probes use this metadata to register with the observation service. The metadata can be extended with information like stage_id microserviceID, method, role, etc. After the registration, the probes will receive communication protocol & configurations to report metrics.
- While the applications are running, the reported metrics are processed by an Observation Agent.
  The Agent must be configured with application name, command, stream configuration including: - Processing window: interval, size - Processing module: specify `parser` and `function` names to process metric reports.
  User must define these processing moduled in `$ROHE_PATH/userModule` (e.g., `userModule/common`), including metric `parser` for parsing metric reports and `function` for window processing.

- To start the Agent, the user can use `rohe-cli`:

```bash
$ rohe-cli observation start-observation-agent --app <application_name> --conf <path_to_agent_configuration> --url <resigstration_service_url>
```

- The Observation service will start the Agent on a container (e.g., Docker container). Metric processing results from the Agent are saved to files or database or message broker (developing) or Prometheus/Grafana (developing) depending on Agent configuration

- To stop the Agent, the user can also use `rohe-cli`:

```bash
$ rohe-cli observation stop-observation-agent --app <application_name> --conf <path_to_agent_configuration> --url <resigstration_service_url>
```

- To delete/unregister an application using `rohe-cli`:

```bash
$ rohe-cli observation delete-app --app <application_name> --url <resigstration_service_url>
```

### 1.2 Development Guide

#### 1.2.1 Registration Service

- This service allows users to register and unregister applications. Service receives commands from REST, developer can modify `core.observation.restService` module to support more commands for editing/updating application.
- Currently this service supports MongoDB as database and AMPQ as communication protocol. The service will also support other communication protocols and databases

#### 1.2.2 Observation Agent

- Agents are currently deployed on the local docker environment: `core.observation.containerizedAgent`.
- To Do: implement remote deployment on several container environments (Docker, Kubernetes, etc).

## 2. Orchestration Service

### 2.1 User Guide

- Prerequisite: before using Orchestration Service, users need:
  - Database service (e.g., MongoDB)
- The Orchestration Service allocate service instances on edge nodes base on a specific orchestration algorithm (currently using scoring algorithm). Users can modify Orchestration Service configurations in `$ROHE_PATH/config/orchestrationConfigLocal.yaml`.
  The configuration defines: - Database configuration where metrics and application data/metadata are stored. - Service queue priority - Orchestration algorithm
- To deploy Orchestration Service, use `rohe-cli`.

```bash
$ rohe-cli start orchestration-service
```

- Add nodes to the orchestration system
  - Users can add nodes by using `rohe-cli`. The node metadata will be saved to the Database
  - When adding nodes, the users must provide file path to the node configurations (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of node configuration is in `$ROHE_PATH/templates/orchestration_command/add_node.yaml`

Example

```bash
$ rohe-cli orchestration add-node --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Add service to the orchestration system
  - Users can add services by using `rohe-cli`. The service metadata will be saved to the Database
  - When adding service, the users must provide file path to the service configurations (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of service configuration is in `$ROHE_PATH/templates/orchestration_command/add_service.yaml`

Example

```bash
$ rohe-cli orchestration add-service --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Get node information from the orchestration system
  - Users can get node information by using `rohe-cli`.
  - To get node information, the users must provide file path to the get command (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of command is in `$ROHE_PATH/templates/orchestration_command/get_node.yaml`

Example

```bash
$ rohe-cli orchestration get-node --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Get service information from the orchestration system
  - Users can get service information by using `rohe-cli`.
  - To get service information, the users must provide file path to the get command (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of command is in `$ROHE_PATH/templates/orchestration_command/get_service.yaml`

Example

```bash
$ rohe-cli orchestration get-service --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Remove nodes from the orchestration system
```bash
$ rohe-cli orchestration remove-node --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```
  - Users can remove node by using `rohe-cli`.
  - To remove nodes, the users must provide file path to the get command (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of command is in `$ROHE_PATH/templates/orchestration_command/remove_node.yaml`

Example

```bash
$ rohe-cli orchestration remove-node --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Start Orchestration Agent
  - Users can start the agent by using `rohe-cli` in the `/bin` folder.
  - Users must provide file path to the get command (`-conf`) and `-url`, the url to the Orchestration Service.
  - The agent constantly check services in the service queue (for services waiting for being allocated). If the service queue is not empty, the agent will find location for allocate the service in the available nodes.
  - The template of command is in `$ROHE_PATH/templates/orchestration_command/start_orchestration.yaml`

Example
```bash
$ rohe-cli orchestration start-agent --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

- Stop Orchestration Agent
  - Users can start the agent by using `rohe-cli` in the `/bin` folder.
  - Users must provide file path to the get command (`-conf`) and `-url`, the url to the Orchestration Service.
  - The template of command is in `$ROHE_PATH/templates/orchestration_command/stop_orchestration.yaml`

```bash
$ rohe-cli orchestration stop-agent --app <application_name> --conf <configuration_path> --url <orchestration_service_url>
```

### 2.2 Development Guide

#### 2.2.1 Resource Management

The module provide the abstract class/object to manage the infrastructure resource by Node; application by Deployment; network routine by Service; and eviroment variable by ConfigMap.

- Node: physical node
- Deployment: each application has multiple microservices. Each microservice has its own Deployment setup specify: image, resource requirement, replicas, etc
- Microservice: each microservice is advertised with a microservice name within K3s network so that other microservices can communicate with it.
- ConfigMap: provide initial environment variable for docker containers of each deployment when starting.
- resource: provide abstract, high-level class to manage resources (Microservice Queue and Node Collection).

#### 2.2.2 Deployment Management

- Provide utilities for generating deployment files from template (`$ROHE_PATH/templates/deployment_template.yaml`)
- Deploy microservices, pod based on generated deployment files
- TO DO: develop abstract function to improve the extendability

#### 2.2.3 Algorithm

This module provide functions to select resource to allocate microservices.

Current implementation: Scoring Algorithm

- Input:

  - Microservice from a microservice Queue (queue of microservice need to be allocated), each microservice in the queue include
    - the number of instances (replicas/scales)
    - CPU requirement (array of CPU requirements on every CPU core). Example: [100,50,50,50] - the microservice use 4 CPUs with 100, 50, 50, and 50 millicpu on each core respectively.
    - Memory requirement (rss, vms - MByte)
    - Accelerator requirement (GPU - %)
    - Sensitivity: 0 - Not sensitive; 1 - CPU sensitive; 2 - Memory sensitive; 3 CPU & Memory sensitive
    - Other metadata: microservice name, ID, status, node (existing deployment), running (existing running instance), container image, ports configuration

  Example:

  ```json
  {
      "EW:VE:TW:WQ:01":{
          "microservice_name":"object_detection_web_service",
          "node": {},
          "status": "queueing",
          "instance_ids": [],
          "running": 0,
          "image": "rdsea/od_web:2.0",
          "ports": [4002],
          "port_mapping": [{
              "con_port": 4002,
              "phy_port": 4002
          },{
              "con_port": 4003,
              "phy_port": 4003
          }],
          "cpu": 550,
          "accelerator": {
              "gpu": 0
          },
          "memory": {
              "rss": 200,
              "vms": 500
          },
          "processor": [500,50],
          "sensitivity": 0,
          "replicas": 2
  }
  ```

  - Node Collection: list of available nodes for allocating microservices each node includes information of capacity and used resources:
    - CPU (millicpu)
    - Memory (rss, vms - MByte)
    - Accelerator (GPU - %)

  Example

  ```json
  "node1":{
      "node_name":"RaspberryPi_01",
      "MAC":"82:ae:30:11:38:01",
      "status": "running",
      "frequency": 1.5,
      "accelerator":{},
      "cpu": {
          "capacity": 4000,
          "used": 0
      },
      "memory": {
          "capacity": {
              "rss": 4096,
              "vms": 4096
          },
          "used": {
              "rss": 0,
              "vms": 0
          }
      },
      "processor": {
          "capacity": [1000,1000,1000,1000],
          "used": [0,0,0,0]
      }
  }, ...
  ```

Workflow of Scoring Algorithm:
![Scoring Workflow](docs/img/workflow_scoring.png)

- Updating Microservice Queue
- Filtering Nodes from the Node Collection
- Scoring filtered node
- Selecting node based on the score, applying different strategies: first/best/worst-fit

- TO DO: define abstract function for each module

## 3 Publications

### On Optimizing Resources for Real‐Time End‐to‐End Machine Learning in Heterogeneous Edges: [Pdf](https://onlinelibrary.wiley.com/doi/pdf/10.1002/spe.3383)

#### Implementation:
- [Observation Service](src/rohe/service/observation_service.py)
- [Observation Abstraction](src/rohe/observation)
- [Orchestration Service](src/rohe/service/orchestration_service.py)
- [Resource Management](src/rohe/orchestration/resource_management)
- [Orchestration Methods](src/rohe/orchestration/orchestration_algorithm)
- Example Application: [BTS](examples/applications/BTS), [CCTVS](examples/applications/cctvs), and KPI (private)
- [Sample Data](datasets/SPE2024)

**Note:** Other publications reuse most parts of this implementation.

Citation:
```bibtex
@article{nguyen2025optimizing,
  title={On Optimizing Resources for Real-Time End-to-End Machine Learning in Heterogeneous Edges},
  author={Nguyen, Minh-Tri and Truong, Hong-Linh},
  journal={Software: Practice and Experience},
  volume={55},
  number={3},
  pages={541--558},
  year={2025},
  publisher={Wiley Online Library}
}
```

### Novel contract-based runtime explainability framework for end-to-end ensemble machine learning serving: [Pdf](https://dl.acm.org/doi/pdf/10.1145/3644815.3644964)
- This publication uses ROHE as the orchestration framework with Observation Service for monitoring and explainability.
- The core abstraction of ML contract can be found in [QoA4ML](https://github.com/rdsea/QoA4ML)
- Example Application: [Malware Detection](https://github.com/rdsea/QoA4ML/tree/main/example/malware_detection/cain_version_outdated) and [CCTVS](examples/applications/cctvs)
- [Sample Data](datasets/CAIN2024)

Citation:
```bibtex
@inproceedings{nguyen2024novel,
  title={Novel contract-based runtime explainability framework for end-to-end ensemble machine learning serving},
  author={Nguyen, Minh-Tri and Truong, Hong-Linh and Truong-Huu, Tram},
  booktitle={Proceedings of the IEEE/ACM 3rd International Conference on AI Engineering-Software Engineering for AI},
  pages={234--244},
  year={2024}
}
```

### Security orchestration with explainability for digital twins-based smart systems: [Pdf](https://research.aalto.fi/files/159919166/submit_compsac2024149909.pdf)
- This publication also uses ROHE as the orchestration framework with Observation Service for monitoring and explainability.
- The core abstraction of ML contract can be found in [RXOMS](https://github.com/rdsea/RXOMS)
- Example Application: [Security in Digital Twins Network](https://github.com/rdsea/RXOMS/tree/main/sdn_simulation)
- User Module: [Performance Evaluation](userModule/sdn.py)

Citation:
```bibtex
@inproceedings{nguyen2024security,
  title={Security orchestration with explainability for digital twins-based smart systems},
  author={Nguyen, Minh-Tri and Lam, An Ngoc and Nguyen, Phu and Truong, Hong-Linh},
  booktitle={2024 IEEE 48th Annual Computers, Software, and Applications Conference (COMPSAC)},
  pages={1194--1203},
  year={2024},
  organization={IEEE}
}
```

### Optimizing Multiple Consumer-specific Objectives in End-to-End Ensemble Machine Learning Serving: [Pdf](https://ieeexplore.ieee.org/iel8/10971776/10971754/10971860.pdf)

#### Implementation:

- [Orchestration Algorithm](src/rohe/orchestration/ensemble_optimization)
- [User Defined Functions](userModule)
- Example Application: [Object Detection](examples/applications/object_classification)
- Example Agent Configuration: [Agent Config](examples/agentConfig)
- [Sample Data](datasets/UCC2024)

Citation:
```bibtex
@inproceedings{nguyen2024optimizing,
  title={Optimizing Multiple Consumer-specific Objectives in End-to-End Ensemble Machine Learning Serving},
  author={Nguyen, Minh-Tri and Truong, Hong-Linh and Arcaini, Paolo and Ishikawa, Fuyuki},
  booktitle={2024 IEEE/ACM 17th International Conference on Utility and Cloud Computing (UCC)},
  pages={103--108},
  year={2024},
  organization={IEEE}
}
```

### IoT Jounal submission (on going)
- [Orchestration Abstraction](src/rohe/orchestration/multimodal_abstration.py)
- Example Application: [Smart building](examples/applications/smart_building), and [Autonomous Robot](examples/applications/) (under maintenance)
- User Module: [Ensemble Selection](userModule/algorithm/multimodal_ensemble.py) and [Custom Workflow](userModule/algorithm/multimodal_workflow.py)
- [Sample Data](datasets/IoT_journal)


### 

<!-- ### User running pipeline
Assume user has application
Explain:
- application: meaning
- client: meaning
- ...


### Scenario 1: obsersvation
Step 1:
- Register application: one time
    - template file for register: example
    - Run client_registrate -> url: "observation:register/"
    return: qoa4ml config

Step 2:
- Enable monitoring: one time
    - Config qoa4ml client using qoa4ml config: example
    - Run: qoa4ml_configurate -> generate qoa4ml client config

Step 3:
- Start observation agent
    - Set function and parser for agent in configuration.json: example: niiStream.config
    - Run start_agent: example: startAgent.sh -> python

Step 4
- Get analysis result from agent:
    - get data from mogodb

### Scenario 2: orchestration
### Scenario 3: ...

Add example contract to 'example/contract'

rename module for icsoc, journal

### Scenario 4: user modify pipeline to use ROHE


 -->



## Authors/Contributors

- Minh-Tri Nguyen
- Hong-Linh Truong
- Vuong Nguyen
- Anh-Dung Nguyen

## License

[Apache License](./LICENSE)
