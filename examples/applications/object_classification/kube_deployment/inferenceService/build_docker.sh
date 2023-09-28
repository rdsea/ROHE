#!/bin/bash

# Build the Docker image
# docker build -t rdsea/nii_inference_service_intel:1.0.1 -f examples/applications/object_classification/kube_deployment/inferenceService/Dockerfile .
# docker rmi -f $(docker images -q --filter "dangling=true")

# docker build -t vtn13042000/nii_inference_service_intel:1.0.0 -f examples/applications/object_classification/kube_deployment/inferenceService/Dockerfile .
# docker build -t vtn13042000/inference:arm -f examples/applications/object_classification/kube_deployment/inferenceService/Dockerfile .
docker build -t vtn13042000/inference:arm_debug -f examples/applications/object_classification/kube_deployment/inferenceService/Dockerfile .


