#! /bin/bash

# Stop all deployments
kubectl delete -f ./ray_cluster/

# Delete namespace
kubectl delete namespace od-ray