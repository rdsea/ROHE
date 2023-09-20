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

COPY ./lib /inference-server/lib

# Copy all other files in the current directory to maintain its relative path in a subfolder
COPY ./examples/applications/object_classification/kube_deployment/inferenceService /inference-server/examples/applications/object_classification/kube_deployment/inferenceService
RUN mkdir /inference-server/artifact

EXPOSE 30005

# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "./examples/applications/object_classification/kube_deployment/inferenceService/server.py", "--conf", "./examples/applications/object_classification/kube_deployment/inferenceService/inference_service.yaml"]
# CMD ["python", "./examples/applications/object_classification/kube_deployment/inferenceService/server.py", "--conf", "./examples/applications/object_classification/kube_deployment/inferenceService/inference_service.yaml", "--enable_qoa", "0"]

