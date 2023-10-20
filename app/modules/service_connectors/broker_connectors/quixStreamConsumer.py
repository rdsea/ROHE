import quixstreams as qx
import pandas as pd

from abc import ABC, abstractmethod

class KafkaStreamListener(ABC):

    def __init__(self, kafka_address: str, topic_name: str):
        self.kafka_address = kafka_address
        self.topic_name = topic_name
        self.client = qx.KafkaStreamingClient(self.kafka_address)
        print("Establish connection")
        self.topic_consumer = self.client.get_topic_consumer(
            self.topic_name, 
            consumer_group=None, 
            auto_offset_reset=qx.AutoOffsetReset.Latest
        )
        self.hook_events()

    def hook_events(self):
        self.topic_consumer.on_stream_received = self.on_stream_received_handler

    def on_stream_received_handler(self, stream_received: qx.StreamConsumer):
        stream_received.timeseries.on_dataframe_received = self.on_dataframe_received_handler

    @abstractmethod
    def on_dataframe_received_handler(self, stream: qx.StreamConsumer, df: pd.DataFrame):
        pass

    def run(self):
        print(f"Listening to streams from topic '{self.topic_name}' at Kafka address '{self.kafka_address}'. Press CTRL-C to exit.")
        qx.App.run()

