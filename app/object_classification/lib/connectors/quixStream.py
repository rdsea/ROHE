import quixstreams as qx
import pandas as pd
# import datetime

from abc import ABC, abstractmethod


class QuixStreamListener(ABC):
    '''
    abstract class with abstract method of handling dataframe message type
    '''
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




class QuixStreamProducer(ABC):
    '''
    abstract class of abstract method of producing message
    '''
    def __init__(self, kafka_address: str, topic_name: str, stream_name: str = "inference_serivce"):
        self.kafka_address = kafka_address
        self.topic_name = topic_name
        self.stream_name = stream_name
        self.client = qx.KafkaStreamingClient(self.kafka_address)
        self.topic_producer = self.client.get_topic_producer(self.topic_name)
        self.stream = self.topic_producer.create_stream()
        self.init_stream()

    def init_stream(self):
        self.stream.properties.name = self.stream_name
        self.stream.properties.metadata["my-metadata"] = "my-metadata-value"
        self.stream.timeseries.buffer.time_span_in_milliseconds = 100  # Send data in 100 ms chunks


    @abstractmethod
    def produce_values(self, message):
        pass

    def close_stream(self):
        print("Closing stream")
        self.stream.close()


    # def produce_values(self, message):
    #     # print("Sending values.")
    #     self.stream.timeseries \
    #         .buffer \
    #         .add_timestamp(datetime.datetime.utcnow()) \
    #         .add_value("request_id", message["request_id"]) \
    #         .add_value("prediction", message["prediction"].tobytes()) \
    #         .add_value("pipeline_id", message["pipeline_id"]) \
    #         .add_value("inference_model_id", message["inference_model_id"]) \
    #         .publish()