FROM python:3.8.15

USER root
WORKDIR /home


RUN apt-get update && apt-get install vim ffmpeg libsm6 libxext6  -y

RUN pip install python-multipart
RUN pip install ipython

RUN pip install numpy==1.24.2
RUN pip install paho-mqtt==1.6.1
RUN pip install pandas==1.5.3
RUN pip install pika==1.3.1
RUN pip install Pillow==9.4.0
RUN pip install psutil==5.9.4
RUN pip install requests==2.28.2
RUN pip install ray==2.3.0
RUN pip install scipy==1.10.1
RUN pip install ultralytics==8.0.49
RUN pip install "ray[serve]"
RUN pip install pymongo==4.3.3
RUN pip install qoa4ml==0.0.67



EXPOSE 8111 8000 6379 8265 10001 52365

# ENTRYPOINT ["tail", "-f", "/dev/null"]
ENTRYPOINT ["/bin/bash", "/home/source/serve.sh"]
