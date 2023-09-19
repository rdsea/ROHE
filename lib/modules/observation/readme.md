The Obervation Agent is implemented in `metric_collector/roheObservationService/roheObservationService.py`.

Before running this service we must start an AMQP broker for communicating via messages and a MongoDB for storing registration information and QoA reports.

The URL of message broker and MongoDB must be specify in `(root-folder)/configurations/observation/observationConfig.json`

Run the service: 

*Note: --conf must be the direct path, if not set, it takes  `(root-folder)/configurations/observation/observationConfig.json` by default
```
python3 roheObservationService.py --conf <configuration-path>
```