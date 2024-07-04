#!/bin/bash

service_dir="$(dirname "$(dirname "$(realpath "$0")")")/service"
if [[ "$1" == "--debug" ]]; then
	flask --app "$service_dir/orchestration_service" run --port 5002 --debug
else
	gunicorn --chdir "$service_dir" "orchestration_service:app"
fi
