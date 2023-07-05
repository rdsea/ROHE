#!/bin/bash

docker build -t rdsea/od_ray_worker:1.0 -f ./Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")
docker push rdsea/od_ray_worker:1.0