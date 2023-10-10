# For testing
FROM python:3.8

WORKDIR /agent

# Copy only requirements.txt first to leverage Docker cache
COPY ./lib/services/observation/agent/requirements.txt /agent/requirements.txt

RUN apt-get update
RUN apt-get install -y gcc python3-dev vim
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./lib /agent/lib
COPY ./configurations /agent/configurations


# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "./lib/services/observation/agent/roheAgentStreaming.py"]
