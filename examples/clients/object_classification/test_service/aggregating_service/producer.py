import quixstreams as qx
import datetime
import argparse



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

        print("Sending values.")

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


if __name__ == "__main__":
    import numpy as np
    import time
    import random
    parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
    parser.add_argument('--kafka_address', type= str, help='default service address', 
                        # default= "kafka.default.svc.cluster.local:9092")
                        default= "localhost:9092")


    args = parser.parse_args()
    kafka_address = args.kafka_address
    print(f"This is the kafka address: {kafka_address}")

    # kafka_address = 'kafka.default.svc.cluster.local:9092'
    # kafka_address = 'localhost:9092'

    # kafka_address = '128.214.254.126:9092'
    # kafka_address = '128.214.254.127:9092'


    # topic_name = 'quickstart-topic'
    topic_name = 'nii_case'

    producer = KafkaStreamProducer(kafka_address, topic_name)

    for i in range(100000000):
        index = random.randint(1, 10)  # Generate a random index for each message

        # index = random.randint(1, 100)  # Generate a random index for each message

        # index = random.randint(101, 110)  # Generate a random index for each message
        # index = random.randint(1, 1000)  # Generate a random index for each message


        random_id = random.randint(1, 200)
        message = {
            "request_id": str(index),
            "prediction": np.array([i, i + 1, i + 2]),
            "pipeline_id": "pipeline_1",
            "inference_model_id": f"model_{random_id}"
        }

        producer.produce_values(message)  # Assuming produce_values expects a list
        # time.sleep(0.0005)
        time.sleep(0.1)
        # time.sleep(0.005)


    producer.close_stream()