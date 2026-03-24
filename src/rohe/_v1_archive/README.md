# V1 Archive

Contains only **dead Flask/Click wrapper code** with zero unique business logic.
All features, algorithms, and integrations have been restored to the active codebase.

## What's Here

| File | Was | Replaced by |
|------|-----|-------------|
| `api/*_resource.py` | Flask-RESTful endpoint wrappers | FastAPI `api/routes/` |
| `cli/rohe_cli/` | Click CLI commands | Typer `cli/` |
| `service/*_service.py` | Flask app factories | FastAPI `service/*_fastapi.py` |

These files contain no business logic -- they are pure HTTP/CLI wrappers around
manager classes that still exist in the active codebase.
