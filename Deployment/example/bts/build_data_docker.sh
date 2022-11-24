#!/bin/bash

docker build -t rdsea/bts_data_proc:2.0 -f ./docker_data_proc/Dockerfile .
docker rmi -f $(docker images -q --filter "dangling=true")
docker push rdsea/bts_data_proc:2.0 