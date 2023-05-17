#!/bin/bash

mkdir workspace
cd workspace
mkdir prometheus_node_exporter
cd prometheus_node_exporter
git clone https://github.com/lipovsek/jetson_prometheus_exporter
sudo apt-get install -y python3-pip
sudo pip3 install virtualenv
virtualenv venv
source venv/bin/activate
pip install prometheus-client==0.7.1 schedule==0.6.0 psutil==5.6.7
cd jetson_prometheus_exporter
python setup.py install
python -m jetson_prometheus_exporter --port 9100