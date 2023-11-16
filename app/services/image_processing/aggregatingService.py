

# import pandas as pd
from app.modules.image_processing.aggregatingObject import KafkaStreamAggregatingListener
from app.object_classification.lib.connectors.storage.mongoDBConnector import MongoDBConnector
from app.object_classification.modules.common import MongoDBInfo

from typing import Callable

class AggregatingService:
    def __init__(self, kafka_address: str, topic_name: str, aggregate_function: Callable,
                 mongodb_info: MongoDBInfo, agg_config: dict):
        self.mongodb_connector = MongoDBConnector(mongodb_info)
        self.kafka_listener = KafkaStreamAggregatingListener(kafka_address, topic_name, aggregate_function= aggregate_function,
                                                             config=agg_config, db_connector= self.mongodb_connector)

    def start_service(self):
        try:
            print("Starting Aggregating Service...")
            self.kafka_listener.run()
        except KeyboardInterrupt:
            print("Shutting down the service...")
