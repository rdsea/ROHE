#!/bin/bash

obser_service="$(dirname $(pwd))/service/observation/observation_service.py"
echo $obser_service
python $obser_service
