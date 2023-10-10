
# For Jetson Xavier AGX J6
FROM arm64v8/python:3.8-slim-buster

# # For testing
# FROM python:3.8-slim-buster

WORKDIR /processing-server

# Copy only requirements.txt first to leverage Docker cache
COPY ./examples/applications/object_classification/kube_deployment/dataProcessingService/requirements.txt /processing-server/requirements.txt

RUN apt-get update
RUN apt-get install -y gcc python3-dev
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./lib /processing-server/lib

# Copy all other files in the current directory to maintain its relative path in a subfolder
COPY ./examples/applications/object_classification/kube_deployment/dataProcessingService /processing-server/examples/applications/object_classification/kube_deployment/dataProcessingService

ENTRYPOINT ["tail", "-f", "/dev/null"]
# CMD ["python", "./examples/applications/object_classification/kube_deployment/dataprocessingService/server.py"]
# CMD ["python3", "./examples/applications/object_classification/kube_deployment/dataProcessingService/server.py", "--conf", "./examples/applications/object_classification/kube_deployment/dataProcessingService/processing_service.yaml"]
