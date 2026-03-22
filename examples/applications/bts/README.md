# BTS (Building Energy Time Series Forecasting) - ROHE Reference Application

A production-grade building energy forecasting pipeline demonstrating ROHE platform integration. Deploys 4 diverse time-series models as independent microservices, orchestrated by the ROHE platform for quality-aware prediction.

## Architecture

```
Client --> Gateway --> Data Ingestion --> [LSTM | GRU | Transformer | Statistical] --> Aggregator
                            |               |       |        |            |
                            +---- rohe-sdk reports metrics to ROHE Observation ----+
```

## Models

| Service | Model | Approach | Speed | Accuracy | Use Case |
|---------|-------|----------|-------|----------|----------|
| lstm | LSTM | Exponential recency weighting | Medium | High | Temporal dependency baseline |
| gru | GRU | Linear decay weighting | Fast | High | Lighter recurrent alternative |
| transformer | Transformer | Self-attention weighting | Slow | Highest | Captures complex patterns |
| statistical | ARIMA/Statistical | Moving average + trend | Very fast | Moderate | Low-cost fallback |

All models accept 6 normalized sensor channels: temperature, humidity, HVAC power, lighting power, occupancy, and solar irradiance.

## Quick Start (Local)

```bash
# Start all services
docker-compose up --build

# In another terminal, send a test forecast request
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"sensor_values": [22.5, 55.0, 12.3, 4.1, 35, 450.0]}'

# Run simulated workload
python client/simulate.py --gateway http://localhost:8000 --rps 5 --duration 60
```

## K8s Deployment

```bash
# Deploy to Kubernetes
kubectl apply -k k8s/

# Verify services are running
kubectl get pods -n bts

# Port-forward gateway
kubectl port-forward -n bts svc/gateway 8000:8000
```

## Running with ROHE Platform

```bash
# Set ROHE environment variables before starting services
export ROHE_ENDPOINT=http://rohe-observation:5010/metrics
export ROHE_EXPERIMENT_ID=exp-001

# Start experiment
rohe experiment start --name "bts-dream" --algorithm dream --contract bts-sla-001

# Run workload
python client/simulate.py --gateway http://localhost:8000 --profile client/workload_profiles/steady_medium.yaml

# Stop and export
rohe experiment stop --name "bts-dream"
rohe export experiment --id bts-dream --output ./results/ --format csv
```

## Workload Profiles

| Profile | RPS | Duration | Description |
|---------|-----|----------|-------------|
| `steady_medium.yaml` | 20 | 10 min | Steady medium load |
| `burst.yaml` | 5 (50 burst) | 10 min | Periodic burst pattern |

## Service Contract

See `contract.yaml` for the SLA definition including:
- Response time p99 < 300ms
- Prediction accuracy >= 80%
- Confidence >= 70%
- Forecast MAE < 0.15 (CDM)
- Prediction variance < 0.10 (CDM)

## Adding a New Model

1. Create `services/new_model_inference/main.py` following the pattern in `lstm_inference/main.py`
2. Add the service to `docker-compose.yml`
3. Add the service URL to gateway's `INFERENCE_SERVICES` env var
4. Create K8s manifest in `k8s/`
5. Set appropriate resource requests/limits based on model complexity
