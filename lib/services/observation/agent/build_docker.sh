#!/bin/bash

# Build the Docker image
docker build -t rdsea/rohe_stream_agent:1.0.0 -f lib/services/observation/agent/Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")