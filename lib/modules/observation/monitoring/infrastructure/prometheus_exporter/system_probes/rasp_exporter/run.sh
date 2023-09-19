#!/bin/bash

wget https://github.com/prometheus/node_exporter/releases/download/v1.1.2/node_exporter-1.1.2.linux-armv7.tar.gz
tar -xvzf node_exporter-1.1.2.linux-armv7.tar.gz 
sudo cp node_exporter-1.1.2.linux-armv7/node_exporter /usr/local/bin
sudo chmod +x /usr/local/bin/node_exporter
sudo useradd -m -s /bin/bash node_exporter
sudo mkdir /var/lib/node_exporter
sudo chown -R node_exporter:node_exporter /var/lib/node_exporter
sudo tee -a /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Node Exporter

[Service]
# Provide a text file location for https://github.com/fahlke/raspberrypi_exporter data with the
# --collector.textfile.directory parameter.
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory /var/lib/node_exporter/textfile_collector

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload 
sudo systemctl enable node_exporter.service
sudo systemctl start node_exporter.service
sudo systemctl status node_exporter.service
