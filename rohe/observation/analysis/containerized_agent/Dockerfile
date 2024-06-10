# For testing
FROM python:3.8

WORKDIR /agent

# Copy only requirements.txt first to leverage Docker cache
COPY ./requirements.txt /agent/requirements.txt

# install necessary libraries/tools
RUN apt-get update
RUN apt-get install -y gcc python3-dev vim
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


# Holding container for debugging
ENTRYPOINT ["tail", "-f", "/dev/null"]

# Run Streamming agent
CMD ["python", "./core/observation/containerizedAgent/roheAgentStreaming.py"]
