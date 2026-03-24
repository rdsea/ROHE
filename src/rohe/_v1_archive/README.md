# V1 Archive

This directory contains legacy code from the ROHE v1 architecture that has been
superseded by the v2 implementation. Code is preserved for reference but is
**not imported by any active module**.

## What's Here

### orchestration/
- `multimodal_orchestration.py` - Legacy multimodal orchestrator (replaced by `orchestrator_v2.py`)
- `multimodal_abstration.py` - Legacy data models (migrated to `models/pipeline.py`, `models/enums.py`)
- `llf_orchestration.py`, `dream_orchestration.py` - Research orchestrators (never integrated)
- `llf.py`, `dream.py` - LLF and DREAM algorithm wrappers
- `allocator.py` - Old allocator (replaced by `allocation/allocator.py`)
- `node_and_service_manager.py` - Old manager (replaced by `allocation/manager.py`)
- `orchestration_algorithm/` - Old algorithm dir (replaced by `allocation/algorithms/`)

### cli/
- `rohe_cli/` - Click-based CLI (replaced by Typer-based `cli/`)

### service/
- `orchestration_service.py` - Flask orchestration service (replaced by FastAPI version)
- `observation_service.py` - Flask observation service (replaced by FastAPI version)

### api/
- `*_resource.py` - Flask-RESTful resources (replaced by FastAPI `routes/`)

### integrations/
- `yolo/` - YOLO v5/v8 wrappers (never imported by active code)
- `consul/` - Consul service registry (replaced by `registry/`)
- `messaging/` - Abstract messaging interface (never implemented)

## V2 Replacements

| V1 Component | V2 Replacement |
|-------------|---------------|
| `multimodal_orchestration.py` | `orchestration/inference/orchestrator_v2.py` |
| `multimodal_abstration.py` | `models/pipeline.py` + `models/enums.py` |
| `rohe_cli/` | `cli/` (Typer) |
| `orchestration_service.py` (Flask) | `service/orchestration_service_fastapi.py` |
| `*_resource.py` (Flask-RESTful) | `api/routes/` (FastAPI) |
| `service_registry/consul.py` | `registry/discovery.py` |
| `orchestration_algorithm/` | `orchestration/allocation/algorithms/` |
