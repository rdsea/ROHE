from __future__ import annotations

from rohe.api.app import create_app
from rohe.api.routes.orchestration import create_orchestration_router
from rohe.common import rohe_utils
from rohe.common.data_models import OrchestrationServiceConfig
from rohe.common.logger import logger
from rohe.orchestration.allocation.manager import NodeAndServiceManager
from rohe.variable import ROHE_PATH

DEFAULT_CONFIG_PATH = "/config/orchestrationConfig.yaml"


def create_orchestration_app():
    """Create FastAPI orchestration service application."""
    config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
    logger.info(f"Loading orchestration config from {config_file}")

    configuration = rohe_utils.load_config(config_file)
    if configuration is None:
        raise RuntimeError(f"Failed to load config from {config_file}")

    orchestration_config = OrchestrationServiceConfig.model_validate(configuration)
    node_and_service_manager = NodeAndServiceManager(orchestration_config)

    app = create_app(title="ROHE Orchestration Service")
    orchestration_router = create_orchestration_router(node_and_service_manager)
    app.include_router(orchestration_router)

    return app
