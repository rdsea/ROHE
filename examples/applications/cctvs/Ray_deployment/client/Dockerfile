FROM python:3.8.15

USER root
WORKDIR /home

RUN apt-get update && apt-get install vim -y

RUN pip install numpy==1.24.2
RUN pip install paho-mqtt==1.6.1
RUN pip install pandas==1.5.3
RUN pip install pika==1.3.1
RUN pip install psutil==5.9.4
RUN pip install requests==2.28.2
RUN pip install qoa4ml==0.0.67
COPY . .


EXPOSE 80 8000 22

# ENTRYPOINT ["tail", "-f", "/dev/null"]
ENTRYPOINT ["python", "/home/client.py"]
