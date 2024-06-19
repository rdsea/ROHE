#!/bin/bash

orches_service="$(dirname "$(realpath "$0")")/../service/orchestration_service"
echo $orches_service
flask --app $orches_service run --port 5002 --debug
