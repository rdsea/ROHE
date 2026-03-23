# Deployment Guide

This guide covers deploying ROHE example applications to local and remote Kubernetes clusters, as well as Docker Compose for quick local testing.

## Architecture Overview

ROHE ships 4 example applications totaling 46 deployments across all apps:

| Application | Deployments | Inference Models |
|---|---|---|
| BTS (Building Time Series) | 10 | LSTM, GRU, Transformer, Statistical |
| CCTVs (Object Detection) | 11 | YOLOv5l, YOLOv8n, YOLOv8s, YOLOv8m, SSD-MobileNet |
| Object Classification | 10 | ResNet50, EfficientNet, MobileNet, ViT |
| Smart Building | 15 | X3D-XS, X3D-S, X3D-M, SlowFast, MiniRocket-SVM, MiniRocket-Ridge, CNN1D, LSTM-TS |

Each application follows a common service topology:

- **Gateway** -- accepts client requests, stores data in DataHub, forwards to orchestrator
- **Orchestrator** -- loads ExecutionPlan from Redis, dispatches preprocessing and inference tasks
- **DataHub** -- data plane for storing raw and preprocessed data
- **Preprocessor / Data Ingestion** -- fetches from DataHub, normalizes, stores back
- **N Inference Services** -- each fetches from DataHub and runs its model
- **Aggregator** -- combines ensemble results using the configured aggregation strategy
- **Redis** -- ExecutionPlan persistence and caching

Smart Building additionally includes a **Data Streamer** service.

## Local Development (kind)

### Prerequisites

- Docker (running)
- [kind](https://kind.sigs.k8s.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

### Install kind and kubectl

```bash
# Install kind
curl -Lo ~/.local/bin/kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
chmod +x ~/.local/bin/kind

# Install kubectl
curl -Lo ~/.local/bin/kubectl "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ~/.local/bin/kubectl

# Verify
kind version
kubectl version --client
```

### Create a kind cluster

```bash
kind create cluster --name rohe-local
```

### Build images

Each application has its own build script under `examples/applications/<app>/scripts/build.sh`.

```bash
cd examples/applications/bts

# Production images (no simulation)
bash scripts/build.sh rdsea 0.0.1

# With simulation baked in (for testing without real models)
bash scripts/build.sh rdsea 0.0.1 true
```

The build script creates one image per service. For BTS, this produces:

```
rdsea/bts-gateway:0.0.1
rdsea/bts-orchestrator:0.0.1
rdsea/bts-data-hub:0.0.1
rdsea/bts-data-ingestion:0.0.1
rdsea/bts-lstm-inference:0.0.1
rdsea/bts-gru-inference:0.0.1
rdsea/bts-transformer-inference:0.0.1
rdsea/bts-statistical-inference:0.0.1
rdsea/bts-aggregator:0.0.1
```

### Deploy

```bash
bash scripts/deploy.sh --local --load-images
```

The `--load-images` flag loads Docker images into the kind cluster via `kind load docker-image`. The deploy script:

1. Creates the namespace (e.g., `bts`)
2. Applies all K8s manifests via `kubectl apply -k k8s/`
3. Waits for all deployments to become ready (timeout: 300s)

### Verify

```bash
kubectl get pods -n bts
kubectl get services -n bts
```

All pods should show `Running` status with `1/1` ready containers.

### Test

```bash
# Port-forward the gateway
kubectl -n bts port-forward svc/gateway 8000:8000

# Send a test request
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data": [22.5, 48.0, 12.3, 4.8, 45, 380.0]}'
```

### Teardown

```bash
bash scripts/teardown.sh
```

To also delete the kind cluster:

```bash
kind delete cluster --name rohe-local
```

## Remote K8s Cluster

### Prerequisites

- `kubectl` configured with a context pointing to the remote cluster
- A container registry accessible from the cluster (e.g., Docker Hub, GCR, ECR)

### Build and push images

```bash
cd examples/applications/bts

# Build with your registry prefix
bash scripts/build.sh myregistry.io/rohe 0.0.1

# Push all images
for img in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep myregistry.io/rohe); do
  docker push "$img"
done
```

### Deploy

```bash
bash scripts/deploy.sh \
  --remote my-remote-context \
  --registry myregistry.io/rohe \
  --tag 0.0.1
```

Additional options:

| Flag | Description |
|---|---|
| `--namespace NS` | Override the default namespace (defaults to app name) |
| `--kubeconfig PATH` | Path to a kubeconfig file |
| `--tag TAG` | Image tag (default: `0.0.1`) |

### Verify

```bash
kubectl --context my-remote-context get pods -n bts
```

## Docker Compose (Quick Local Testing)

Each application provides `docker-compose.yml` (production) and `docker-compose.sim.yml` (simulation overlay) under `examples/applications/<app>/`.

### Production mode

```bash
cd examples/applications/bts
docker compose -f docker-compose.yml up
```

### Simulation mode

The simulation overlay mounts sim config files and sample registries into inference containers:

```bash
cd examples/applications/bts
docker compose -f docker-compose.yml -f docker-compose.sim.yml up
```

The gateway is exposed on `localhost:8000` by default.

### Stop

```bash
docker compose down
```

## Configuration

### Environment Variables

Key environment variables used across services:

| Variable | Used By | Description |
|---|---|---|
| `ORCHESTRATOR_URL` | Gateway | URL of the orchestrator service (e.g., `http://orchestrator:9000`) |
| `DATA_HUB_URL` | Gateway, Orchestrator | URL of the DataHub service |
| `PIPELINE_ID` | Gateway | Pipeline identifier (e.g., `bts`) |
| `REDIS_URL` | Orchestrator | Redis connection string for plan persistence |
| `MODEL_CONFIG` | Inference services | Path to model simulation config YAML |
| `ROHE_SERVICE_NAME` | All services | Service identifier for observability |
| `EXECUTION_PLANS_DIR` | Orchestrator | Directory containing ExecutionPlan YAML files |
| `EVICT_AFTER_QUERY` | Orchestrator | Whether to evict data from DataHub after query (`true`/`false`) |
| `REQUEST_TIMEOUT_SECONDS` | Orchestrator | Timeout for inter-service HTTP calls (default: `30`) |

### ExecutionPlan

The ExecutionPlan defines which models run, their weights, and the aggregation strategy. Plans are loaded from YAML files at startup and persisted to Redis.

Example structure (`sim_config/execution_plan.yaml`):

```yaml
pipeline_id: bts
version: 1
aggregator_url: "http://aggregator:8000/aggregate"
data_hub_url: "http://data-hub:8000"

modality_ensembles:
  timeseries:
    modality: timeseries
    preprocessor:
      service_url: "http://data-ingestion:8000/preprocess"
      preprocessor_id: bts-normalizer
      output_data_key: timeseries_normalized
    ensemble_members:
      - service_id: lstm
        inference_url: "http://lstm-inference:8000/inference"
        weight: 1.0
        is_active: true
      - service_id: gru
        inference_url: "http://gru-inference:8000/inference"
        weight: 0.9
        is_active: true
    selection_strategy: enhance_confidence
    aggregation_strategy: confidence_weighted

execution_phases:
  - phase_id: 0
    modalities: [timeseries]
    is_conditional: false
```

### Runtime Modification

The orchestrator exposes REST endpoints to inspect and modify plans at runtime without redeployment:

```bash
# Port-forward the orchestrator
kubectl -n bts port-forward svc/orchestrator 9000:9000

# Get the current plan
curl http://localhost:9000/plans/bts

# Patch the ensemble for a modality (e.g., deactivate a model)
curl -X PATCH http://localhost:9000/plans/bts/ensemble/timeseries \
  -H "Content-Type: application/json" \
  -d '{
    "ensemble_members": [
      {"service_id": "lstm", "weight": 1.0, "is_active": true},
      {"service_id": "gru", "weight": 0.9, "is_active": false},
      {"service_id": "transformer", "weight": 1.0, "is_active": true},
      {"service_id": "statistical", "weight": 0.6, "is_active": true}
    ]
  }'
```

This updates the plan in Redis immediately. The orchestrator picks up changes on the next request.
