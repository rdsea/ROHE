# processing server
# examples/applications/object_classification/kube_deployment/dataProcessingService
timeout 10m python ./dataProcessingService/server.py --conf ./dataProcessingService/processing_service.yaml &
echo "Starting processing service"