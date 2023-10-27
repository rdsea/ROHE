
import datetime

from app.object_classification.lib.connectors.quixStream import QuixStreamProducer



class QuixStreamDataframeProducer(QuixStreamProducer):
    def __init__(self, kafka_address: str, topic_name: str):
        super().__init__(kafka_address, topic_name)
    

    def produce_values(self, message):
        # print("Sending values.")
        self.stream.timeseries \
            .buffer \
            .add_timestamp(datetime.datetime.utcnow()) \
            .add_value("request_id", message["request_id"]) \
            .add_value("prediction", message["prediction"].tobytes()) \
            .add_value("pipeline_id", message["pipeline_id"]) \
            .add_value("inference_model_id", message["inference_model_id"]) \
            .publish()