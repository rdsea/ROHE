# Quickstart: Deploy ROHE + BTS in 10 Minutes

This guide walks through deploying the BTS (Building Time Series) application on a local kind cluster. BTS is the simplest example app with 4 inference models (LSTM, GRU, Transformer, Statistical) behind a single gateway.

## 1. Clone the repo

```bash
git clone https://github.com/rdsea/ROHE.git
cd ROHE
```

## 2. Install kind and kubectl

```bash
curl -Lo ~/.local/bin/kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
chmod +x ~/.local/bin/kind

curl -Lo ~/.local/bin/kubectl "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ~/.local/bin/kubectl
```

## 3. Create a cluster

```bash
kind create cluster --name rohe-local
```

## 4. Build BTS images with simulation

```bash
cd examples/applications/bts
bash scripts/build.sh rdsea 0.0.1 true
```

This builds 9 images (gateway, orchestrator, data-hub, data-ingestion, 4 inference services, aggregator) with simulation code baked in so no real ML models are needed.

## 5. Deploy BTS

```bash
bash scripts/deploy.sh --local --load-images
```

Wait for all pods to become ready:

```bash
kubectl get pods -n bts -w
```

Expected output: 10 pods (9 services + 1 Redis), all `Running` with `1/1` ready.

## 6. Send a test request

```bash
# In a separate terminal, port-forward the gateway
kubectl -n bts port-forward svc/gateway 8000:8000
```

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"data": [22.5, 48.0, 12.3, 4.8, 45, 380.0]}' | python3 -m json.tool
```

You should see a JSON response with `query_id`, `ensemble_result`, and `model_count`.

## 7. Check orchestrator plans

```bash
# In a separate terminal
kubectl -n bts port-forward svc/orchestrator 9000:9000
```

```bash
curl -s http://localhost:9000/plans/bts | python3 -m json.tool
```

This returns the active ExecutionPlan showing all 4 models, their weights, and the aggregation strategy.

## 8. Modify the ensemble at runtime

Deactivate GRU to see the ensemble adapt without redeployment:

```bash
curl -s -X PATCH http://localhost:9000/plans/bts/ensemble/timeseries \
  -H "Content-Type: application/json" \
  -d '{
    "ensemble_members": [
      {"service_id": "lstm", "weight": 1.0, "is_active": true},
      {"service_id": "gru", "weight": 0.9, "is_active": false},
      {"service_id": "transformer", "weight": 1.0, "is_active": true},
      {"service_id": "statistical", "weight": 0.6, "is_active": true}
    ]
  }' | python3 -m json.tool
```

Send another predict request -- the response `model_count` should now be 3 instead of 4.

## 9. Run the client

The BTS client sends sustained traffic and logs results to CSV:

```bash
cd examples/applications/bts

python client/client.py \
  --gateway http://localhost:8000 \
  --rps 5 \
  --duration 60 \
  --output ./results/client_results.csv
```

This sends 5 requests per second for 60 seconds (300 total) and writes per-request metrics to `results/client_results.csv`.

## 10. View results

```bash
head -5 results/client_results.csv
```

Columns: `query_id`, `timestamp`, `sample_id`, `ground_truth`, `response_time_ms`, `top_prediction`, `confidence`, `model_count`, `status`.

## Cleanup

```bash
bash scripts/teardown.sh
kind delete cluster --name rohe-local
```

## Next Steps

- See the full [Deployment Guide](deployment.md) for remote clusters and Docker Compose
- Explore other apps: `cctvs`, `object_classification`, `smart_building`
- Run experiments from the `experiments/` directory
