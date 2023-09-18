# FROM arm64v8/python:3.8-slim-buster
# FROM python:3.8-slim-buster
# FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3

FROM python:3.8

WORKDIR /inference-server

# Copy only requirements.txt first to leverage Docker cache
COPY ./examples/applications/object_classification/kube_deployment/inferenceService/requirements.txt /inference-server/requirements.txt

RUN apt-get update
RUN pip3 install -r requirements.txt

# Copy the specific files, maintaining directory structure for lib
COPY ./lib/object_classification/modules/classificationObject.py /inference-server/lib/object_classification/modules/classificationObject.py
COPY ./lib/object_classification/services/objectClassificationService.py /inference-server/lib/object_classification/services/objectClassificationService.py
COPY ./lib/service_connectors/boto3StorageConnector.py /inference-server/lib/service_connectors/boto3StorageConnector.py
COPY ./lib/service_connectors/minioStorageConnector.py /inference-server/lib/service_connectors/minioStorageConnector.py
COPY ./lib/roheClassificationObject.py /inference-server/lib/roheClassificationObject.py
COPY ./lib/roheObject.py /inference-server/lib/roheObject.py
COPY ./lib/restService.py /inference-server/lib/restService.py

# Copy all other files in the current directory to maintain its relative path in a subfolder
COPY ./examples/applications/object_classification/kube_deployment/inferenceService /inference-server/examples/applications/object_classification/kube_deployment/inferenceService

EXPOSE 9000

ENTRYPOINT ["tail", "-f", "/dev/null"]
# CMD ["python", "app.py"]
