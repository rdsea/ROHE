# For Jetson Xavier AGX J6
# FROM arm64v8/python:3.8-slim-buster

# Not working
# FROM python:3.8-slim-buster
# FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3

# For testing
FROM python:3.8

WORKDIR /inference-server

# Copy only requirements.txt first to leverage Docker cache
COPY ./examples/applications/object_classification/kube_deployment/inferenceService/requirements.txt /inference-server/requirements.txt

RUN apt-get update
RUN apt-get install -y gcc python3-dev
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# Copy the specific files, maintaining directory structure for lib
# COPY ./lib/object_classification/modules/classificationObject.py /inference-server/lib/object_classification/modules/classificationObject.py
# COPY ./lib/object_classification/services/objectClassificationService.py /inference-server/lib/object_classification/services/objectClassificationService.py
# COPY ./lib/service_connectors/boto3StorageConnector.py /inference-server/lib/service_connectors/boto3StorageConnector.py
# COPY ./lib/service_connectors/minioStorageConnector.py /inference-server/lib/service_connectors/minioStorageConnector.py
# COPY ./lib/roheClassificationObject.py /inference-server/lib/roheClassificationObject.py
# COPY ./lib/roheObject.py /inference-server/lib/roheObject.py
# COPY ./lib/restService.py /inference-server/lib/restService.py
COPY ./lib /inference-server/lib

# Copy all other files in the current directory to maintain its relative path in a subfolder
COPY ./examples/applications/object_classification/kube_deployment/inferenceService /inference-server/examples/applications/object_classification/kube_deployment/inferenceService
RUN mkdir /inference-server/artifact

EXPOSE 30005

# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "./examples/applications/object_classification/kube_deployment/inferenceService/server.py"]
