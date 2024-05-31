#!/bin/bash

obser_service="$(dirname $(pwd))/service/observation_service.py"
echo $obser_service
python $obser_service
