#!/bin/bash

orches_service="$(dirname $(pwd))/service/orchestration_service.py"
echo $orches_service
python $orches_service
