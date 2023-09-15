from qoa4ml.collector.amqp_collector import Amqp_Collector
import qoa4ml.qoaUtils as qoaUtils

connetor_conf = qoaUtils.load_config("./config.json")
client = Amqp_Collector(connetor_conf['amqp_collector']['conf'])
client.start()