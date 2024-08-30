# For Jetson Xavier AGX J6
FROM arm64v8/python:3.8-slim-buster

# Not working
# FROM python:3.8-slim-buster
# FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3

# For testing
# FROM python:3.8

WORKDIR /aggregate-server

# Copy only requirements.txt first to leverage Docker cache
COPY ./examples/applications/object_classification/kube_deployment/aggregatingService/requirements.txt /aggregate-server/requirements.txt

RUN apt-get update
RUN apt-get install -y gcc python3-dev
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./lib /aggregate-server/lib

# Copy all other files in the current directory to maintain its relative path in a subfolder
COPY ./examples/applications/object_classification/kube_deployment/aggregatingService /aggregate-server/examples/applications/object_classification/kube_deployment/aggregatingService


ENTRYPOINT ["tail", "-f", "/dev/null"]
# CMD ["python", "./examples/applications/object_classification/kube_deployment/aggregatingService/server.py", "--conf", "./examples/applications/object_classification/kube_deployment/aggregatingService/configurations/aggregating_service.yaml"]

