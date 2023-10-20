import sys
import json
from qoa4ml import qoaUtils as utils
from qoa4ml.collector.amqp_collector import Amqp_Collector
from threading import Thread

lib_path = utils.get_parent_dir(__file__,3)
sys.path.append(lib_path)

from lib.modules.observation.streamAnalysis.parser import OCParser


class Collector(object):
    def __init__(self, config) -> None:
        self.config = config
        self.collector = Amqp_Collector(self.config["collector"], self)
        self.subthread = Thread(target=self.collector.start)
        
    def start(self):
        self.subthread.start()

    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))
        result = OCParser(mess, self.config["parser_config"])
        # print(result)
    
    def stop(self):
        self.collector.stop()