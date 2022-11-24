#!/bin/bash

docker build -t rdsea/od_proc:2.0 -f ./Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")
docker push rdsea/od_proc:2.0