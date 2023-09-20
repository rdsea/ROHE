#!/bin/bash

docker build -t rdsea/od_ray_light:1.1 -f ./Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")
docker push rdsea/od_ray_light:1.1