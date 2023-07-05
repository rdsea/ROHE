from qoa4ml.collector.amqp_collector import Amqp_Collector
import qoa4ml.utils as utils

connetor_conf = utils.load_config("./config.json")
client = Amqp_Collector(connetor_conf['amqp_collector']['conf'])
client.start()