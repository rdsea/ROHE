# Monitoring System

The current Monitoring system is build based on Prometheus.

A container running Prometheus will collect system information from all the physiscal node.
This information will be used in the provisioning algorithm to distribute the workload, scaling the service, control service elasticity and so on.

In later step, it will also collect data about service qualities.

## Node exporter

Edge devices are diverse and need specific node exporter to collect data depending on its hardware architecture for example arm, adm, x32, x64, CPUs, GPUs, TPUs, NPUs, and so on

- Raspberry Pi: the exporter for Raspberry Pi 4 running on Ubuntu-arm64 is showing in folder `rasp_exporter`
- Jetson Nano: Developing...
- Coral DevBoard: Developing..
- Rock Pi N10: Developing