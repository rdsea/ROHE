import quixstreams as qx
import datetime


class KafkaStreamProducer:
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

    def produce_values(self, message):
        # print("Sending values.")

        # for pred in predictions:
        self.stream.timeseries \
            .buffer \
            .add_timestamp(datetime.datetime.utcnow()) \
            .add_value("request_id", message["request_id"]) \
            .add_value("prediction", message["prediction"].tobytes()) \
            .add_value("pipeline_id", message["pipeline_id"]) \
            .add_value("inference_model_id", message["inference_model_id"]) \
            .publish()


    def close_stream(self):
        print("Closing stream")
        self.stream.close()