#!/bin/bash

# Build the Docker image
docker build -t rdsea/nii_inference_service_intel:1.0.1 -f examples/applications/object_classification/kube_deployment/inferenceService/Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")
# docker build -t vtn13042000/nii_inference_service_intel:2.0.0 -f examples/applications/NII/kube_deployment/inferenceService/Dockerfile .
