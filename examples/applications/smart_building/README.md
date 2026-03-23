# Smart Building

Multi-modal activity recognition combining video and sensor streams.

## Architecture

```
Client -> Control Plane -> DataHub -> Orchestrator -> Preprocessor -> Inference Services -> Aggregator -> Control Plane -> Client
```

### Services

| Service | Image | Description |
|---------|-------|-------------|
| Control Plane | rdsea/smart-building-control-plane | Accepts requests, stores data in DataHub, forwards to orchestrator |
| Orchestrator | rdsea/smart-building-orchestrator | Loads ExecutionPlan, dispatches preprocessing and inference |
| DataHub | rdsea/smart-building-data-hub | Data plane: stores raw and preprocessed data |
| Data Streamer | rdsea/smart-building-data-streamer | Continuous sensor streaming into DataHub |
| Preprocessor | rdsea/smart-building-preprocessor | Fetches from DataHub, normalizes, stores back |
| X3D-XS | rdsea/smart-building-x3d-xs-inference | Fetches from DataHub, runs X3D Extra Small video inference |
| X3D-S | rdsea/smart-building-x3d-s-inference | Fetches from DataHub, runs X3D Small video inference |
| X3D-M | rdsea/smart-building-x3d-m-inference | Fetches from DataHub, runs X3D Medium video inference |
| SlowFast | rdsea/smart-building-slowfast-r50-inference | Fetches from DataHub, runs SlowFast R50 video inference |
| MiniRocket+SVM | rdsea/smart-building-minirocket-svm-inference | Fetches from DataHub, runs MiniRocket+SVM timeseries inference |
| MiniRocket+Ridge | rdsea/smart-building-minirocket-ridge-inference | Fetches from DataHub, runs MiniRocket+Ridge timeseries inference |
| CNN1D | rdsea/smart-building-cnn1d-inference | Fetches from DataHub, runs 1D CNN timeseries inference |
| LSTM-TS | rdsea/smart-building-lstm-ts-inference | Fetches from DataHub, runs LSTM timeseries inference |
| Aggregator | rdsea/smart-building-aggregator | Combines results from ensemble |
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
kubectl -n smart-building port-forward svc/control-plane 8000:8000
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data":"sb-00001","modalities":["video","timeseries"]}'
```

### Teardown
```bash
bash scripts/teardown.sh
```

## Simulation

Simulation code is gitignored and baked into images with `INCLUDE_SIM=true`.

### Sim Config Files
- `sim_config/x3d_xs.yaml` - X3D Extra Small simulation config (accuracy, latency, hardware)
- `sim_config/x3d_s.yaml` - X3D Small simulation config
- `sim_config/x3d_m.yaml` - X3D Medium simulation config
- `sim_config/slowfast_r50.yaml` - SlowFast R50 simulation config
- `sim_config/minirocket_svm.yaml` - MiniRocket+SVM simulation config
- `sim_config/minirocket_ridge.yaml` - MiniRocket+Ridge simulation config
- `sim_config/cnn1d.yaml` - CNN1D simulation config
- `sim_config/lstm_ts.yaml` - LSTM timeseries simulation config
- `sim_config/samples.yaml` - sample registry for ground truth tracking
- `sim_config/client.yaml` - client simulation config
- `sim_config/execution_plan.yaml` - ExecutionPlan defining the ensemble
- `sim_config/hardware_profiles/` - hardware device profiles (latency multipliers)
- `sim_config/scenarios/` - quality scenarios (high_accuracy, low_latency, degraded, etc.)

### Switching Models
Edit the ExecutionPlan via the orchestrator API:
```bash
kubectl -n smart-building port-forward svc/orchestrator 9000:9000
# Get current plan
curl http://localhost:9000/plans/{pipeline_id}
# Patch ensemble (e.g., remove a video model)
curl -X PATCH http://localhost:9000/plans/{pipeline_id}/ensemble/video \
  -H "Content-Type: application/json" -d '{...}'
# Patch ensemble (e.g., remove a timeseries model)
curl -X PATCH http://localhost:9000/plans/{pipeline_id}/ensemble/timeseries \
  -H "Content-Type: application/json" -d '{...}'
```

## Client

```bash
python client/client.py --gateway http://localhost:8000 --rps 5 --duration 60
```

The client sends `modalities`, `window_length`, and `time_constraint_ms` -- no raw data payload. Sensor modalities include `video`, `timeseries`, `acc_phone`, `acc_watch`, `gyro`, and `orientation`.
