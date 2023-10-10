#!/bin/bash

# Save the current working directory
MAIN_DIR=$(pwd)

# start container service
cd "$MAIN_DIR" # Navigate back to the main directory
# start mqtt broker
cd ./data-storage-broker/mqtt_broker
docker-compose up -d
echo "Starting docker container for mqtt broker"

cd "$MAIN_DIR" # Navigate back to the main directory
# Start redis 
cd ./data-storage-broker/redis
docker-compose up -d
echo "Starting docker container for redis"

cd "$MAIN_DIR" # Navigate back to the main directory
# start mongodb server
cd ./data-storage-broker/mongodb_server
docker-compose up -d
echo "Starting docker container for mongodb server"

cd "$MAIN_DIR" # Navigate back to the main directory
# start kafka server
cd ./data-storage-broker/kafka_server
docker-compose up -d
echo "Starting docker container for kafka server"
sleep 30
docker-compose up -d


# # start pipeline
# cd "$MAIN_DIR" # Navigate back to the main directory

# conda init bash
# conda activate rohe
# # examples/applications/object_classification/kube_deployment/dataIngestionService
# # start ingestion service
# timeout 10m python ./dataIngestionService/server.py --conf ./dataIngestionService/server.py/ingestion_service.yaml &
# echo "Starting ingestion service"

# # start task coordinator
# # examples/applications/object_classification/kube_deployment/dataProcessingService/task_coordinator
# timeout 10m python ./dataProcessingService/task_coordinator/task_coordinator.py --conf ./dataProcessingService/task_coordinator/task_coordinator.yaml &
# echo "Starting tasking coordinator"

# # processing server
# # examples/applications/object_classification/kube_deployment/dataProcessingService
# timeout 10m python ./dataProcessingService/server.py --conf ./dataProcessingService/inference_server.yaml &
# echo "Starting processing service"

# # inference_service
# # examples/applications/object_classification/kube_deployment/dataProcessingService
# timeout 10m python ./inferenceService/server.py --conf ./inferenceService/configurations/inference_service.yaml &
# echo "Starting inference service"


# # conda deactivate
