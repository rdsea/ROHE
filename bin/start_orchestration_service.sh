#!/bin/bash

orches_service="$(dirname $(pwd))/service/orchestration/orchestration_service.py"
echo $orches_service
python $orches_service
