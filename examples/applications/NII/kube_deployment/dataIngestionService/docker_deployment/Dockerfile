# FROM python:3.9
# FROM arm64v8/python:3.8-slim-buster
FROM python:3.8-slim-buster
# FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3


WORKDIR /ingestion-server

# Copy only requirements.txt first to leverage Docker cache
COPY ./requirements.txt /ingestion-server/requirements.txt

RUN apt-get update
RUN pip3 install -r requirements.txt

# Copy all other files
COPY . /ingestion-server/

# EXPOSE 9000

ENTRYPOINT ["tail", "-f", "/dev/null"]
# CMD ["python", "app.py"]
