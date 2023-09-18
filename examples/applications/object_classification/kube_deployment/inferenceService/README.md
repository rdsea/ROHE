To build the docker image, run the build_docker.sh script.

## Building the Docker Image

### 1. Navigate to the Project's Main Directory
Make sure you are in the main directory of the project, which is called "ROHE".

### 2. Run the build_docker.sh script
/home/vtn/aalto-internship/ROHE/examples/applications/object_classification/kube_deployment/inferenceService/build_docker.sh
Note: The build_docker.sh script must be run from the main directory to ensure that the file and folder hierarchy in the Docker container matches the project structure. The script and the sample Dockerfile provide details on how to maintain this hierarchy. Any file added should also follow this copy pattern.

## Run the Docker Container
### 1. Edit docker-compose file
Before running the Docker Compose command, locate the volumes section in the Docker Compose YAML file. Change the directory path for the model data to match the local directory where your models are stored.

### 2. Run Docker Compose
Use the docker-compose up command to start the container services defined in the Docker Compose file.
` docker-compose up -d `

### 3. Access the Running Container
Identify the container ID using docker ps and then exec into the container's shell.

` docker exec -it <container-id> /bin/bash `

### 4. Run the application
Once inside the container, execute the following command to start the application:
` python3 examples/applications/object_classification/kube_deployment/inferenceService/server.py `