# Jetson Nano Exporter:
The current node exporter is an [open-source project](https://github.com/lipovsek/jetson_prometheus_exporter)

Requirement:
- Python 3
- schedule: 0.6.0
- prometheus-client :0.7.1
- psutil: 5.6.7

Clone source code and install:
```
$ git clone <source code>
$ python3 setup.py install
```

# Creat Exporter service
After creating the virtual env, installing all the requirements & jetson_prometheus_exporter, we can create a service for automatic export system metrices.

- Creat script file in `/usr/bin/<service_name>.sh`.
For Example:
```bash
$ sudo vim /usr/bin/gpumonitor.sh 
```
Content:
```bash
#!/bin/bash

source /home/aaltosea/workspace/prometheus_node_exporter/venv/bin/activate
python -m jetson_prometheus_exporter --port 9101
```

- Create service file. For example:
```bash
$ sudo vim /etc/systemd/system/monitorgpu.service
```
Content:
```bash
[Unit]
Description=Monitoring GPU
After=multi-user.target
StartLimitIntervalSec=5

[Service]
Type=simple
RestartSec=1
Restart=always
ExecStart=/usr/bin/gpumonitor.sh
[Install]
WantedBy=multi-user.target
```

- Enable the new service:
```bash
$ sudo systemctl daemon-reload 
$ sudo systemctl enable monitorgpu.service 
$ sudo systemctl start monitorgpu.service
```