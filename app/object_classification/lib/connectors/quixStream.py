import quixstreams as qx
import pandas as pd
import datetime

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

    @abstractmethod
    def on_stream_received_handler(self, stream_received: qx.StreamConsumer):
        pass
    
    # def on_stream_received_handler(self, stream_received: qx.StreamConsumer):
    #     stream_received.timeseries.on_dataframe_received = self.on_dataframe_received_handler

    # @abstractmethod
    # def on_dataframe_received_handler(self, stream: qx.StreamConsumer, df: pd.DataFrame):
    #     pass

    def run(self):
        print(f"Listening to streams from topic '{self.topic_name}' at Kafka address '{self.kafka_address}'. Press CTRL-C to exit.")
        qx.App.run()


class QuixStreamDataframeHandler(QuixStreamListener):
    def __init__(self, kafka_address: str, topic_name: str, 
                host_object):
        super().__init__(kafka_address, topic_name)
        self.host_object = host_object

    def on_stream_received_handler(self, stream_received: qx.StreamConsumer):
        stream_received.timeseries.on_dataframe_received = self.host_object.on_receive_data_as_dataframe
        

# class QuixStreamProducer(ABC):
class QuixStreamProducer():
    '''

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

    def close_stream(self):
        print("Closing stream")
        self.stream.close()

    # send all the item in the dictionary
    def produce_values(self, message: dict):
        # print("Sending values.")
        # Initialize the buffer and add the timestamp
        buffer = self.stream.timeseries.buffer.add_timestamp(datetime.datetime.utcnow())

        # Loop over each key-value pair in the message and add them to the buffer
        for key, value in message.items():
            print(f'about to add key {key} with value {value}')
            buffer.add_value(key, value)

        # Publish the buffer
        buffer.publish()