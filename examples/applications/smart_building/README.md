# Smart Building - ROHE Reference Application

A multi-modal activity recognition pipeline demonstrating ROHE platform integration. Combines video and time-series models as independent microservices, orchestrated by the ROHE platform for quality-aware inference across modalities.

## Architecture

```
Client --> Control Plane --> [Video Models]      --> Aggregator
                         |     X3D-XS | X3D-S | X3D-M | SlowFast
                         |
                         --> [Time-Series Models] --> Aggregator
                               MiniRocket+SVM | MiniRocket+Ridge | CNN1D | LSTM
                         |
                         --> Data Hub (cache)
                               |
                               +---- rohe-sdk reports metrics to ROHE Observation ----+
```

## Models

### Video Modality

| Service | Model | Speed | Accuracy | Use Case |
|---------|-------|-------|----------|----------|
| x3d-xs | X3D Extra Small | Very fast | Lower | Real-time edge |
| x3d-s | X3D Small | Fast | Moderate | Balanced |
| x3d-m | X3D Medium | Slow | Highest | Best quality |
| slowfast | SlowFast R50 | Moderate | High | Alternative architecture |

### Time-Series Modality

| Service | Model | Speed | Accuracy | Use Case |
|---------|-------|-------|----------|----------|
| minirocket-svm | MiniRocket + SVM | Very fast | Good | Feature-based baseline |
| minirocket-ridge | MiniRocket + Ridge | Fastest | Moderate | Lightweight classifier |
| cnn1d | 1D CNN | Fast | Moderate | Deep learning baseline |
| lstm-ts | LSTM | Moderate | Best | Sequential patterns |

Activity classes: walking, sitting, standing, running, cooking, cleaning, eating, reading.

## Quick Start (Local)

```bash
# Start all services
docker-compose up --build

# Send a multi-modal inference query
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"modalities": ["video", "timeseries"], "time_constraint_ms": 500}'

# Run simulated workload
python client/client.py --control-plane http://localhost:8000 --rps 5 --duration 60

# Video-only workload
python client/client.py --control-plane http://localhost:8000 --modalities video --rps 10

# Time-series-only workload
python client/client.py --control-plane http://localhost:8000 --modalities timeseries --rps 20
```

## K8s Deployment

```bash
# Deploy to Kubernetes
kubectl apply -k k8s/

# Verify services are running
kubectl get pods -n smart-building

# Port-forward control plane
kubectl port-forward -n smart-building svc/control-plane 8000:8000
```

## Running with ROHE Platform

```bash
# Set ROHE environment variables before starting services
export ROHE_ENDPOINT=http://rohe-observation:5010/metrics
export ROHE_EXPERIMENT_ID=exp-001

# Start experiment
rohe experiment start --name "smart-building-dream" --algorithm dream --contract smart-building-sla-001

# Run workload
python client/client.py --control-plane http://localhost:8000 --profile client/workload_profiles/steady_medium.yaml

# Stop and export
rohe experiment stop --name "smart-building-dream"
rohe export experiment --id smart-building-dream --output ./results/ --format csv
```

## Workload Profiles

| Profile | RPS | Duration | Modalities | Description |
|---------|-----|----------|------------|-------------|
| `steady_medium.yaml` | 20 | 10 min | Both | Steady medium load |
| `burst.yaml` | 5 (50 burst) | 10 min | Both | Periodic burst pattern |
| `multimodal.yaml` | 10 | 10 min | Both | Relaxed time constraint for full fusion |

## Service Contract

See `contract.yaml` for the SLA definition including:
- Response time p99 < 800ms
- Accuracy >= 80%
- Confidence >= 65%
- Per-modality accuracy CDMs (video >= 75%, timeseries >= 70%)
- Cross-modal agreement >= 60%

## Adding a New Model

1. Create `services/new_model_inference/main.py` following the pattern in `x3d_xs_inference/main.py` (video) or `minirocket_svm_inference/main.py` (timeseries)
2. Add the service to `docker-compose.yml`
3. Add the service URL to control plane's `VIDEO_SERVICES` or `TIMESERIES_SERVICES` env var
4. Create K8s manifest in `k8s/` and add to `kustomization.yaml`
5. Set appropriate resource requests/limits (GPU for video models, CPU for timeseries)
