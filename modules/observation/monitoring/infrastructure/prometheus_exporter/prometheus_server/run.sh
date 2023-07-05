#!/bin/bash

docker run -p 9090:9090 -v /Users/tringuyen/workplace/Study/PhD/Gitlab/elamlserving/monitoring/system_monitoring/prometheus_server/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus