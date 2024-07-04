#!/bin/bash

service_dir="$(dirname "$(dirname "$(realpath "$0")")")/service"
if [[ "$1" == "--debug" ]]; then
	flask --app "$service_dir/observation_service" run --port 5002 --debug
else
	gunicorn --chdir "$service_dir" "observation_service:app"
fi
