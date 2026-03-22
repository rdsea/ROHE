# CCTVS Object Detection - ROHE Reference Application

A production-grade object detection pipeline demonstrating ROHE platform integration. Deploys 5 diverse detection models as independent microservices with a preprocessing stage, orchestrated by the ROHE platform for quality-aware inference.

## Architecture

```
Client --> Web Gateway --> Preprocessor --> [YOLOv5L | YOLOv8N | YOLOv8S | YOLOv8M | SSD-MobileNet] --> Aggregator
                                                |          |         |         |            |
                                                +---- rohe-sdk reports metrics to ROHE Observation ----+
```

## Models

| Service | Model | Parameters | Speed | Accuracy | Use Case |
|---------|-------|-----------|-------|----------|----------|
| yolov5l | YOLOv5 Large | ~46M | Moderate | High | High-accuracy baseline |
| yolov8n | YOLOv8 Nano | ~3M | Very fast | Lower | Edge / real-time |
| yolov8s | YOLOv8 Small | ~11M | Fast | Moderate | Balanced speed/accuracy |
| yolov8m | YOLOv8 Medium | ~26M | Moderate | High | General purpose |
| ssd-mobilenet | SSD MobileNet | ~6M | Fastest | Lower | Ultra-low latency |

All models produce simulated detections for classes: car, person, truck, bicycle, bus, motorcycle, dog, cat.

## Quick Start (Local)

```bash
# Start all services
docker-compose up --build

# In another terminal, send a test image
curl -X POST http://localhost:8000/detect \
  -F "image=@test_frame.jpg"

# Run simulated workload
python client/simulate.py --gateway http://localhost:8000 --rps 5 --duration 60
```

## K8s Deployment

```bash
# Deploy to Kubernetes
kubectl apply -k k8s/

# Verify services are running
kubectl get pods -n cctvs

# Port-forward gateway
kubectl port-forward -n cctvs svc/web-gateway 8000:8000
```

## Running with ROHE Platform

```bash
# Set ROHE environment variables before starting services
export ROHE_ENDPOINT=http://rohe-observation:5010/metrics
export ROHE_EXPERIMENT_ID=exp-001

# Start experiment
rohe experiment start --name "cctvs-dream" --algorithm dream --contract cctvs-sla-001

# Run workload
python client/simulate.py --gateway http://localhost:8000 --profile client/workload_profiles/steady_medium.yaml

# Stop and export
rohe experiment stop --name "cctvs-dream"
rohe export experiment --id cctvs-dream --output ./results/ --format csv
```

## Workload Profiles

| Profile | RPS | Duration | Description |
|---------|-----|----------|-------------|
| `steady_medium.yaml` | 20 | 10 min | Steady medium load |
| `burst.yaml` | 5 (50 burst) | 10 min | Periodic burst pattern |

## Service Contract

See `contract.yaml` for the SLA definition including:
- Response time p99 < 300ms
- Accuracy >= 80%
- Confidence >= 60%
- Misclassification rate < 15% (CDM)
- False positive rate < 10% (CDM)

## Adding a New Model

1. Create `services/new_model_inference/main.py` following the pattern in `yolov5l_inference/main.py`
2. Add the service to `docker-compose.yml`
3. Add the service URL to web-gateway's `INFERENCE_SERVICES` env var
4. Create K8s manifest in `k8s/`
5. Set appropriate resource requests/limits based on model size
