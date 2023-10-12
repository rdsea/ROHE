#!/bin/bash

obser_service="$(dirname `pwd`)/core/observation/roheObservationService.py"
echo $obser_service
python $obser_service
 
