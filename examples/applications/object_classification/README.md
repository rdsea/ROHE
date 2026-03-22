# Object Classification - ROHE Reference Application

A production-grade image classification pipeline demonstrating ROHE platform integration. Deploys 4 diverse ML models as independent microservices, orchestrated by the ROHE platform for quality-aware inference.

## Architecture

```
Client --> Gateway --> [ResNet-50 | EfficientNet-B0 | MobileNetV3 | ViT-B/16] --> Aggregator
                            |            |              |            |
                            +---- rohe-sdk reports metrics to ROHE Observation ----+
```

## Models

| Service | Model | Parameters | Speed | Accuracy | Use Case |
|---------|-------|-----------|-------|----------|----------|
| resnet50 | ResNet-50 | ~25M | Medium | High | CNN baseline |
| efficientnet | EfficientNet-B0 | ~5M | Fast | High | Best accuracy/compute ratio |
| mobilenet | MobileNetV3-Small | ~2.5M | Very fast | Moderate | Edge-optimized |
| vit | ViT-B/16 | ~86M | Slow | Highest | Vision transformer |

All models are pretrained on ImageNet (1000 classes).

## Quick Start (Local)

```bash
# Start all services
docker-compose up --build

# In another terminal, send a test image
curl -X POST http://localhost:8000/classify \
  -F "image=@test_image.jpg"

# Run simulated workload
python client/simulate.py --gateway http://localhost:8000 --rps 5 --duration 60
```

## K8s Deployment

```bash
# Deploy to Kubernetes
kubectl apply -k k8s/

# Verify services are running
kubectl get pods -n object-classification

# Port-forward gateway
kubectl port-forward -n object-classification svc/gateway 8000:8000
```

## Running with ROHE Platform

```bash
# Set ROHE environment variables before starting services
export ROHE_ENDPOINT=http://rohe-observation:5010/metrics
export ROHE_EXPERIMENT_ID=exp-001

# Start experiment
rohe experiment start --name "obj-class-dream" --algorithm dream --contract obj-class-sla-001

# Run workload
python client/simulate.py --gateway http://localhost:8000 --profile client/workload_profiles/steady_medium.yaml

# Stop and export
rohe experiment stop --name "obj-class-dream"
rohe export experiment --id obj-class-dream --output ./results/ --format csv
```

## Workload Profiles

| Profile | RPS | Duration | Description |
|---------|-----|----------|-------------|
| `steady_medium.yaml` | 20 | 10 min | Steady medium load |
| `burst.yaml` | 5 (50 burst) | 10 min | Periodic burst pattern |

## Service Contract

See `contract.yaml` for the SLA definition including:
- Response time p99 < 500ms
- Accuracy >= 85%
- Confidence >= 70%
- Top-5 error rate < 10% (CDM)

## Adding a New Model

1. Create `services/new_model_inference/main.py` following the pattern in `resnet50_inference/main.py`
2. Add the service to `docker-compose.yml`
3. Add the service URL to gateway's `INFERENCE_SERVICES` env var
4. Create K8s manifest in `k8s/`
5. Set appropriate resource requests/limits based on model size
