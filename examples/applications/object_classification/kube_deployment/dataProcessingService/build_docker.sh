# docker build -t vtn13042000/nii_ingestion_service_intel:1.0.0 -f examples/applications/object_classification/kube_deployment/dataIngestionService/Dockerfile .
# docker build -t vtn13042000/processing:arm -f examples/applications/object_classification/kube_deployment/dataProcessingService/Dockerfile .
docker build -t vtn13042000/processing:arm_debug -f examples/applications/object_classification/kube_deployment/dataProcessingService/Dockerfile .


