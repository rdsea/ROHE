from __future__ import annotations

from qoa4ml.config.configs import CollectorConfig, ConnectorConfig

from rohe.api.app import create_app
from rohe.api.routes.observation import (
    create_agent_manager_router,
    create_registration_router,
)
from rohe.common import rohe_utils
from rohe.common.data_models import MongoAuthentication, MongoCollection
from rohe.common.logger import logger
from rohe.observation.agent_manager import AgentManager
from rohe.observation.registration_manager import RegistrationManager
from rohe.storage.mongo import MDBClient
from rohe.variable import ROHE_PATH

DEFAULT_CONFIG_PATH = "/config/observationConfig.yaml"


def create_observation_app():
    """Create FastAPI observation service application."""
    config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
    logger.info(f"Loading observation config from {config_file}")

    configuration = rohe_utils.load_config(config_file)
    if configuration is None:
        raise RuntimeError(f"Failed to load config from {config_file}")

    db_config = MongoAuthentication(**configuration["db_authentication"])
    db_collection = MongoCollection(**configuration["db_collection"])
    db_client = MDBClient(db_config)

    connector_config = ConnectorConfig(**configuration["connector"])
    collector_config = CollectorConfig(**configuration["collector"])

    registration_manager = RegistrationManager(
        db_client, db_collection, connector_config, collector_config
    )
    agent_manager = AgentManager(
        db_client, db_collection, configuration["agent_image"]
    )

    app = create_app(title="ROHE Observation Service")
    app.include_router(create_registration_router(registration_manager))
    app.include_router(create_agent_manager_router(agent_manager))

    return app
