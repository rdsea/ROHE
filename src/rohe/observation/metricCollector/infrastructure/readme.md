# Infrastructure Monitoring
The system can be monitored in several layers:
- Physical: some system metrics are exposed by specific exporters and collected by a Prometheus server.
Node exporter is the system service specific for each physical machine: Raspberry Pi and Jetson.
Users or collector programs can query these metrics from Prometheus.
The metrics are exposed with different names specified in the metric maps
- VM: a client program connect to host service (docker/K3s daemon) to query real-time metrics.
    - Docker: Monitor VM resource usage at runtime.
    - K3s: Monitor deployment status, resource usages, number of replicas/scale at runtime.

[comment]: <> (rsync -av -e ssh --exclude='dataset' ./* aaltosea@edge-k3s-j6.cs.aalto.fi:/home/aaltosea/workspace/elamlserving)