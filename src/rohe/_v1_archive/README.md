# V1 Archive

This directory contains **old infrastructure code** that has been replaced by
v2 implementations. These are NOT algorithms or research code -- they are old
service patterns (Flask, Click, Consul) that will not be used again.

Research algorithms (AdaptiveOrchestrator, DREAM, LLF, ensemble selection,
phase assignment) are in the **active codebase** at `src/rohe/orchestration/`
and `userModule/algorithm/`.

## What's Here (old infrastructure only)

| Directory | Contents | Replaced by |
|-----------|----------|-------------|
| `cli/rohe_cli/` | Click-based CLI | Typer `cli/` |
| `service/` | Flask orchestration + observation services | FastAPI `service/*_fastapi.py` |
| `api/` | Flask-RESTful resources | FastAPI `api/routes/` |
| `integrations/yolo/` | YOLO v5/v8 wrappers | Not needed |
| `integrations/consul/` | Consul service registry | `registry/discovery.py` |
| `integrations/messaging/` | Abstract messaging (never implemented) | Not needed |
| `experiment/` | Experiment manager (to re-integrate) | `experiments/` directory |
| `export/` | Paper export utilities (to re-integrate) | `experiments/common/analysis/` |
