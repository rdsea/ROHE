#!/bin/bash

obser_service="$(dirname $(pwd))/service/observation_service.py"
echo $orches_service
flask --app $orches_service run --port 5010 --debug
