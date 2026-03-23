# Object Classification

Image classification with ensemble of CNN and transformer models.

## Architecture

```
Client -> Gateway -> DataHub -> Orchestrator -> Preprocessor -> Inference Services -> Aggregator -> Gateway -> Client
```

### Services

| Service | Image | Description |
|---------|-------|-------------|
| Gateway | rdsea/object-classification-gateway | Accepts requests, stores data in DataHub, forwards to orchestrator |
| Orchestrator | rdsea/object-classification-orchestrator | Loads ExecutionPlan, dispatches preprocessing and inference |
| DataHub | rdsea/object-classification-data-hub | Data plane: stores raw and preprocessed data |
| Preprocessor | rdsea/object-classification-preprocessor | Fetches from DataHub, normalizes, stores back |
| ResNet-50 | rdsea/object-classification-resnet50-inference | Fetches from DataHub, runs ResNet-50 inference |
| EfficientNet-B0 | rdsea/object-classification-efficientnet-b0-inference | Fetches from DataHub, runs EfficientNet-B0 inference |
| MobileNetV3 | rdsea/object-classification-mobilenet-v3-small-inference | Fetches from DataHub, runs MobileNetV3-Small inference |
| ViT-B/16 | rdsea/object-classification-vit-b-16-inference | Fetches from DataHub, runs ViT-B/16 inference |
| Aggregator | rdsea/object-classification-aggregator | Combines results from ensemble |
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
kubectl -n object-classification port-forward svc/gateway 8000:8000
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data":"objclass-00001","modalities":["image"]}'
```

### Teardown
```bash
bash scripts/teardown.sh
```

## Simulation

Simulation code is gitignored and baked into images with `INCLUDE_SIM=true`.

### Sim Config Files
- `sim_config/resnet50.yaml` - ResNet-50 simulation config (accuracy, latency, hardware)
- `sim_config/efficientnet_b0.yaml` - EfficientNet-B0 simulation config
- `sim_config/mobilenet_v3_small.yaml` - MobileNetV3-Small simulation config
- `sim_config/vit_b_16.yaml` - ViT-B/16 simulation config
- `sim_config/samples.yaml` - sample registry for ground truth tracking
- `sim_config/client.yaml` - client simulation config
- `sim_config/execution_plan.yaml` - ExecutionPlan defining the ensemble
- `sim_config/hardware_profiles/` - hardware device profiles (latency multipliers)
- `sim_config/scenarios/` - quality scenarios (high_accuracy, low_latency, degraded, etc.)

### Switching Models
Edit the ExecutionPlan via the orchestrator API:
```bash
kubectl -n object-classification port-forward svc/orchestrator 9000:9000
# Get current plan
curl http://localhost:9000/plans/{pipeline_id}
# Patch ensemble (e.g., remove a model)
curl -X PATCH http://localhost:9000/plans/{pipeline_id}/ensemble/image \
  -H "Content-Type: application/json" -d '{...}'
```

## Client

```bash
python client/client.py --gateway http://localhost:8000 --rps 5 --duration 60

# With class-labeled image dataset
python client/client.py --gateway http://localhost:8000 --dataset /path/to/images/
```
