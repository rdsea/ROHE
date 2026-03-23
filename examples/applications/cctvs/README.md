# CCTVS (CCTV Surveillance)

Object detection from surveillance camera feeds.

## Architecture

```
Client -> Web Gateway -> DataHub -> Orchestrator -> Preprocessor -> Inference Services -> Aggregator -> Web Gateway -> Client
```

### Services

| Service | Image | Description |
|---------|-------|-------------|
| Web Gateway | rdsea/cctvs-web-gateway | Accepts requests, stores data in DataHub, forwards to orchestrator |
| Orchestrator | rdsea/cctvs-orchestrator | Loads ExecutionPlan, dispatches preprocessing and inference |
| DataHub | rdsea/cctvs-data-hub | Data plane: stores raw and preprocessed data |
| Preprocessor | rdsea/cctvs-preprocessor | Fetches from DataHub, normalizes, stores back |
| YOLOv5L | rdsea/cctvs-yolov5l-inference | Fetches from DataHub, runs YOLOv5 Large inference |
| YOLOv8N | rdsea/cctvs-yolov8n-inference | Fetches from DataHub, runs YOLOv8 Nano inference |
| YOLOv8S | rdsea/cctvs-yolov8s-inference | Fetches from DataHub, runs YOLOv8 Small inference |
| YOLOv8M | rdsea/cctvs-yolov8m-inference | Fetches from DataHub, runs YOLOv8 Medium inference |
| SSD-MobileNet | rdsea/cctvs-ssd-mobilenet-inference | Fetches from DataHub, runs SSD MobileNet inference |
| Aggregator | rdsea/cctvs-aggregator | Combines results from ensemble |
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
kubectl -n cctvs port-forward svc/web-gateway 8000:8000
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data":"cctvs-00001","modalities":["image"]}'
```

### Teardown
```bash
bash scripts/teardown.sh
```

## Simulation

Simulation code is gitignored and baked into images with `INCLUDE_SIM=true`.

### Sim Config Files
- `sim_config/yolov5l.yaml` - YOLOv5 Large simulation config (accuracy, latency, hardware)
- `sim_config/yolov8n.yaml` - YOLOv8 Nano simulation config
- `sim_config/yolov8s.yaml` - YOLOv8 Small simulation config
- `sim_config/yolov8m.yaml` - YOLOv8 Medium simulation config
- `sim_config/ssd_mobilenet.yaml` - SSD MobileNet simulation config
- `sim_config/samples.yaml` - sample registry for ground truth tracking
- `sim_config/client.yaml` - client simulation config
- `sim_config/execution_plan.yaml` - ExecutionPlan defining the ensemble
- `sim_config/hardware_profiles/` - hardware device profiles (latency multipliers)
- `sim_config/scenarios/` - quality scenarios (high_accuracy, low_latency, degraded, etc.)

### Switching Models
Edit the ExecutionPlan via the orchestrator API:
```bash
kubectl -n cctvs port-forward svc/orchestrator 9000:9000
# Get current plan
curl http://localhost:9000/plans/{pipeline_id}
# Patch ensemble (e.g., remove a model)
curl -X PATCH http://localhost:9000/plans/{pipeline_id}/ensemble/image \
  -H "Content-Type: application/json" -d '{...}'
```

## Client

```bash
python client/client.py --gateway http://localhost:8000 --rps 5 --duration 60

# With image dataset
python client/client.py --gateway http://localhost:8000 --dataset /path/to/images/
```
