#!/bin/bash

service_dir="$(dirname "$(dirname "$(realpath "$0")")")/service"
rm "$ROHE_PATH/temp/deployment/*"
if [[ "$1" == "--debug" ]]; then
	flask --app "$service_dir/orchestration_service" run --port 5002 --debug
else
	gunicorn -b 0.0.0.0:5002 --chdir "$service_dir" "orchestration_service:app"
fi
