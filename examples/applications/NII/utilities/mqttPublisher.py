import paho.mqtt.client as mqtt
import json
import logging

class MqttPublisher:

    def __init__(self, broker_info, client_id, pub_topic):
        self.client_id = client_id
        self.pub_topic = pub_topic

        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)
        self.client.connect(broker_info['url'], broker_info['port'], broker_info['keepalive'])
        self.client.loop_start()

    def send_data(self, body_mess):
        self.client.publish(self.pub_topic, json.dumps(body_mess), qos=0)

    def stop(self):
        self.client.disconnect()
