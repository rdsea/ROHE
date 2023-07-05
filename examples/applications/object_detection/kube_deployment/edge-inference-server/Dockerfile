#FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3
#RUN apt update
#RUN apt install -y git wget make build-essential manpages-dev python2-dev
#
#COPY /usr/local/cuda/ /usr/local/cuda/
#WORKDIR /inference
#
#RUN git clone https://github.com/pjreddie/darknet.git
##COPY ./darknet /inference/darknet
#RUN cd darknet
#
#WORKDIR /inference/darknet
#RUN make GPU=1
#
#RUN wget https://pjreddie.com/media/files/yolov3-tiny.weights
#
##install web-server dependencies
#RUN wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
#RUN python2 get-pip.py
#COPY requirements.txt requirements.txt
#RUN ["mkdir", "/inference/temp"]
#
#RUN pip install -r requirements.txt
#COPY ./*.py /inference/darknet/ 
## Injecting customized python version for calling the object detection
#
#EXPOSE 4002
#CMD ["gunicorn", "-k", "eventlet", "-b", "0.0.0.0:4002", "server:app"]

FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3
RUN apt update
RUN apt install -y git wget make build-essential manpages-dev python3-pip vim

WORKDIR /inference

RUN git clone https://github.com/pjreddie/darknet.git
RUN cd darknet

WORKDIR /inference/darknet
RUN make GPU=1

RUN wget https://pjreddie.com/media/files/yolov3-tiny.weights

#install web-server dependencies
# RUN wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
# RUN python2 get-pip.py
COPY requirements.txt requirements.txt
RUN ["mkdir", "/inference/temp"]

# Injecting customized python version for calling the object detection

RUN apt-get update
RUN apt-get -o Dpkg::Options::="--force-confmiss" install -y --reinstall netbase
RUN pip3 install -r requirements.txt
RUN pip3 install qoa4ml==0.0.59
COPY . . 

EXPOSE 4002
# ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["gunicorn", "-k", "eventlet", "-b", "0.0.0.0:4002", "server:app"]