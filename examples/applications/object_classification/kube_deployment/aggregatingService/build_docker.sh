#!/bin/bash

# Build the Docker image
docker build -t vtn13042000/aggregate:arm_debug -f examples/applications/object_classification/kube_deployment/aggregatingService/Dockerfile .


