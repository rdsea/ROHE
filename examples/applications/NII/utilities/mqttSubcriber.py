import paho.mqtt.client as mqtt
import logging

class MqttSubscriber:

    def __init__(self, host_object, broker_info, client_id, sub_topic):
        self.host_object = host_object
        self.client_id = client_id
        self.sub_topic = sub_topic

        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(broker_info['url'], broker_info['port'], broker_info['keepalive'])
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug("Connected with result code " + str(rc))
        self.client.subscribe(self.sub_topic)

    def on_message(self, client, userdata, msg):
        logging.debug(f"Received message from topic {msg.topic}")
        self.host_object.message_processing(client, userdata, msg)

    def stop(self):
        self.client.disconnect()
