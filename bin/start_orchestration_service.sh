#!/bin/bash

orches_service="$(dirname `pwd`)/core/orchestration/roheOrchestrationService.py"
echo $orches_service
python $orches_service
 
