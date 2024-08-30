import copy
import time
import uuid
from typing import Any, Dict

from qoa4ml.config.configs import (
    AMQPCollectorConfig,
    AMQPConnectorConfig,
    CollectorConfig,
    ConnectorConfig,
)

from ..common.data_models import MongoCollection
from ..common.logger import logger
from ..storage.mongo import MDBClient


class RegistrationManager:
    def __init__(
        self,
        db_client: MDBClient,
        db_collection: MongoCollection,
        connector_config: ConnectorConfig,
        collector_config: CollectorConfig,
    ) -> None:
        try:
            self.db_client = db_client
            self.db_collection = db_collection
            self.connector_config: ConnectorConfig = connector_config

            self.collector_config: CollectorConfig = collector_config

            assert isinstance(self.connector_config.config, AMQPConnectorConfig)

            assert isinstance(self.collector_config.config, AMQPCollectorConfig)
        except Exception as e:
            logger.exception(f"Error in `__init__` RoheRegistration: {e}")

    def get_app(self, application_name: str):
        """
        Get application configuration from database
        """
        try:
            query = [
                {"$sort": {"timestamp": 1}},
                {
                    "$group": {
                        "_id": "$app_id",
                        "application_name": {"$last": "$application_name"},
                        "user_id": {"$last": "$user_id"},
                        "run_id": {"$last": "$run_id"},
                        "timestamp": {"$last": "$timestamp"},
                        "db": {"$last": "$db"},
                        "client_count": {"$last": "$client_count"},
                        "agent_config": {"$last": "$agent_config"},
                    }
                },
            ]
            app_list = list(self.db_client.get(self.db_collection, query))
            # Get application from application list
            for app in app_list:
                if app["application_name"] == application_name:
                    return app
            return None
        except Exception as e:
            logger.exception(f"Error in `get_app` RoheRegistration: {e}")
            return None

    def update_app(self, metadata: Dict):
        """
        Update application configuration
        """
        try:
            return self.db_client.insert_one(self.db_collection, metadata)
        except Exception as e:
            logger.exception(f"Error in `update_app` RoheRegistration: {e}")
            return {}

    def generate_agent_conf(self, metadata: Dict) -> dict:
        try:
            # Database configuration
            agent_db_config = copy.deepcopy(self.db_collection)
            agent_db_config.database = (
                "application_" + metadata["application_name"] + "_" + metadata["app_id"]
            )
            agent_db_config.collection = "metric_collection_" + metadata["run_id"]
            # Collector configuration

            collector = copy.deepcopy(self.collector_config)

            assert isinstance(collector.config, AMQPCollectorConfig)
            i_config = collector.config
            i_config.exchange_name = str(metadata["application_name"]) + "_exchange"
            i_config.in_routing_key = str(metadata["application_name"]) + ".#"
            agent_config = {}
            agent_config["db_authentication"] = self.db_client.to_dict()
            agent_config["db_collection"] = agent_db_config.model_dump()
            agent_config["collector"] = collector.model_dump()
            return agent_config
        except Exception as e:
            logger.exception(f"Error in `generate_agent_conf` RoheRegistration: {e}")
            return {}

    def register_app(self, application_name: str, run_id: str, user_id: str) -> dict:
        try:
            # Create new application configuration and push to database
            metadata: Dict[str, Any] = {}
            metadata["application_name"] = application_name
            metadata["run_id"] = run_id
            metadata["user_id"] = user_id
            metadata["app_id"] = str(uuid.uuid4())
            metadata["db"] = (
                "application_" + application_name + "_" + metadata["app_id"]
            )
            metadata["timestamp"] = time.time()
            metadata["client_count"] = 1
            metadata["agent_config"] = self.generate_agent_conf(metadata)
            self.db_client.insert_one(self.db_collection, metadata)
            return metadata
        except Exception as e:
            logger.exception(f"Error in `register_app` RoheRegistration: {e}")
            return {}

    def delete_app(self, application_name: str, run_id: str, user_id: str):
        application = {
            "application_name": application_name,
            "run_id": run_id,
            "user_id": user_id,
        }
        self.db_client.delete_many(self.db_collection, application)
