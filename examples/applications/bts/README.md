# BTS (Building Time Series)

Time-series forecasting for building energy management.

## Architecture

```
Client -> Gateway -> DataHub -> Orchestrator -> Data Ingestion -> Inference Services -> Aggregator -> Gateway -> Client
```

### Services

| Service | Image | Description |
|---------|-------|-------------|
| Gateway | rdsea/bts-gateway | Accepts requests, stores data in DataHub, forwards to orchestrator |
| Orchestrator | rdsea/bts-orchestrator | Loads ExecutionPlan, dispatches preprocessing and inference |
| DataHub | rdsea/bts-data-hub | Data plane: stores raw and preprocessed data |
| Data Ingestion | rdsea/bts-data-ingestion | Fetches from DataHub, normalizes, stores back |
| LSTM | rdsea/bts-lstm-inference | Fetches from DataHub, runs LSTM inference |
| GRU | rdsea/bts-gru-inference | Fetches from DataHub, runs GRU inference |
| Transformer | rdsea/bts-transformer-inference | Fetches from DataHub, runs transformer inference |
| Statistical | rdsea/bts-statistical-inference | Fetches from DataHub, runs statistical inference |
| Aggregator | rdsea/bts-aggregator | Combines results from ensemble |
| Redis | redis:7-alpine | ExecutionPlan persistence |

## Quick Start

### Build
```bash
# Without simulation (production)
bash scripts/build.sh rdsea 0.0.1

# With simulation (for testing)
bash scripts/build.sh rdsea 0.0.1 true
```

### Deploy to Local K8s (kind)
```bash
bash scripts/deploy.sh --local --load-images
```

### Test
```bash
kubectl -n bts port-forward svc/gateway 8000:8000
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data":"bts-00001","modalities":["timeseries"]}'
```

### Teardown
```bash
bash scripts/teardown.sh
```

## Simulation

Simulation code is gitignored and baked into images with `INCLUDE_SIM=true`.

### Sim Config Files
- `sim_config/lstm.yaml` - LSTM simulation config (accuracy, latency, hardware)
- `sim_config/gru.yaml` - GRU simulation config
- `sim_config/transformer.yaml` - Transformer simulation config
- `sim_config/statistical.yaml` - Statistical simulation config
- `sim_config/samples.yaml` - sample registry for ground truth tracking
- `sim_config/client.yaml` - client simulation config
- `sim_config/execution_plan.yaml` - ExecutionPlan defining the ensemble
- `sim_config/hardware_profiles/` - hardware device profiles (latency multipliers)
- `sim_config/scenarios/` - quality scenarios (high_accuracy, low_latency, degraded, etc.)

### Switching Models
Edit the ExecutionPlan via the orchestrator API:
```bash
kubectl -n bts port-forward svc/orchestrator 9000:9000
# Get current plan
curl http://localhost:9000/plans/{pipeline_id}
# Patch ensemble (e.g., remove a model)
curl -X PATCH http://localhost:9000/plans/{pipeline_id}/ensemble/timeseries \
  -H "Content-Type: application/json" -d '{...}'
```

## Client

```bash
python client/client.py --gateway http://localhost:8000 --rps 5 --duration 60

# With CSV dataset
python client/client.py --gateway http://localhost:8000 --dataset /path/to/data.csv --mode simulated
```
