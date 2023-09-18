# FROM arm64v8/python:3.8-slim-buster
FROM python:3.8-slim-buster


WORKDIR /task-coordinator-service

# Copy only requirements.txt first to leverage Docker cache
COPY ./requirements.txt /task-coordinator-service/requirements.txt

RUN apt-get update
RUN pip3 install -r requirements.txt

# Copy all other files
COPY . /task-coordinator-service/

EXPOSE 5000

ENTRYPOINT ["tail", "-f", "/dev/null"]
# CMD ["python", "app.py"]
