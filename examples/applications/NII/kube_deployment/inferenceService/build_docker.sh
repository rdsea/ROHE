#!/bin/bash

# Build the Docker image
docker build -t vtn13042000/nii_inference_service_intel:2.0.0 -f examples/applications/NII/kube_deployment/inferenceService/Dockerfile .
