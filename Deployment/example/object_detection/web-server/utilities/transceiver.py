import pika, uuid

headers = {
        'Content-Type': 'application/json'
    }

class Amqp_Transceiver(object):
    def __init__(self, config):
        self.config = config
        self.exchange_name = config["exchange_name"]
        self.exchange_type = config["exchange_type"]
        self.routing_key = config["routing_key"]
        self.client_id = config["client_id"] 
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=config["url"]))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type=self.exchange_type)

    def stop(self):
        #self.channel.close()
        self.connection.close()

    def send(self, mess, metadata=None):
        # Sending data to desired destination
        # if sender is client, it will include the "reply_to" attribute to specify where to reply this message
        # if sender is server, it will reply the message to "reply_to" via default exchange 
        try:
            corr_id = uuid.uuid4().hex
            self.sub_properties = pika.BasicProperties(correlation_id=corr_id)
            self.channel.basic_publish(exchange=self.exchange_name,routing_key=self.routing_key,properties=self.sub_properties,body=mess)
            self.channel.waitForConfirms(1000)
        except Exception as e:
            print("Amqp sending data unsuccessful {}".format(e))

