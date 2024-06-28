#!/bin/bash

obser_service="$(dirname "$(realpath "$0")")/../service/observation_service"
echo "$obser_service"
flask --app "$obser_service" run --port 5010 --debug
