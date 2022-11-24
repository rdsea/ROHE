#!/bin/bash

docker build -t rdsea/bts_ml_proc:2.0 -f ./docker_ml/Dockerfile .
docker rmi $(docker images -q --filter "dangling=true")
docker push rdsea/bts_ml_proc:2.0