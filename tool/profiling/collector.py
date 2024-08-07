import json
import os
import sys
from threading import Thread

from qoa4ml.collector.amqp_collector import Amqp_Collector

ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)


class Collector:
    def __init__(self, config) -> None:
        self.config = config
        self.collector = Amqp_Collector(self.config["collector"], self)
        self.subthread = Thread(target=self.collector.start)

    def start(self):
        self.subthread.start()

    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))
        # result = OCParser(mess, self.config["parser_config"])
        # print(result)

    def stop(self):
        self.collector.stop()
